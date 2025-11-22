"""
FastAPI backend for AnyCoder - provides REST API endpoints
"""
from fastapi import FastAPI, HTTPException, Header, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, AsyncGenerator
import json
import asyncio
from datetime import datetime, timedelta
import secrets
import base64
import urllib.parse
import re

# Import only what we need, avoiding Gradio UI imports
import sys
import os
from huggingface_hub import InferenceClient
import httpx

# Import model handling from backend_models
from backend_models import (
    get_inference_client, 
    get_real_model_id,
    create_gemini3_messages,
    is_native_sdk_model,
    is_mistral_model
)

# Import project importer for importing from HF/GitHub
from project_importer import ProjectImporter

# Import system prompts from standalone backend_prompts.py
# No dependencies on Gradio or heavy libraries
print("[Startup] Loading system prompts from backend_prompts...")

try:
    from backend_prompts import (
        HTML_SYSTEM_PROMPT,
        TRANSFORMERS_JS_SYSTEM_PROMPT,
        STREAMLIT_SYSTEM_PROMPT,
        REACT_SYSTEM_PROMPT,
        get_gradio_system_prompt,  # Import the function to get dynamic prompt
        JSON_SYSTEM_PROMPT,
        GENERIC_SYSTEM_PROMPT
    )
    # Get the Gradio system prompt (includes full Gradio 6 documentation)
    GRADIO_SYSTEM_PROMPT = get_gradio_system_prompt()
    print("[Startup] ✅ All system prompts loaded successfully from backend_prompts.py")
    print(f"[Startup] 📚 Gradio system prompt loaded with full documentation ({len(GRADIO_SYSTEM_PROMPT)} chars)")
except Exception as e:
    import traceback
    print(f"[Startup] ❌ ERROR: Could not import from backend_prompts: {e}")
    print(f"[Startup] Traceback: {traceback.format_exc()}")
    print("[Startup] Using minimal fallback prompts")
    
    # Define minimal fallback prompts
    HTML_SYSTEM_PROMPT = "You are an expert web developer. Create complete HTML applications with CSS and JavaScript."
    TRANSFORMERS_JS_SYSTEM_PROMPT = "You are an expert at creating transformers.js applications. Generate complete working code."
    STREAMLIT_SYSTEM_PROMPT = "You are an expert Streamlit developer. Create complete Streamlit applications."
    REACT_SYSTEM_PROMPT = "You are an expert React developer. Create complete React applications with Next.js."
    GRADIO_SYSTEM_PROMPT = "You are an expert Gradio developer. Create complete, working Gradio applications."
    JSON_SYSTEM_PROMPT = "You are an expert at generating JSON configurations. Create valid, well-structured JSON."
    GENERIC_SYSTEM_PROMPT = "You are an expert {language} developer. Create complete, working {language} applications."

print("[Startup] System prompts initialization complete")

# Cache system prompts map for fast lookup (created once at startup)
SYSTEM_PROMPT_CACHE = {
    "html": HTML_SYSTEM_PROMPT,
    "gradio": GRADIO_SYSTEM_PROMPT,
    "streamlit": STREAMLIT_SYSTEM_PROMPT,
    "transformers.js": TRANSFORMERS_JS_SYSTEM_PROMPT,
    "react": REACT_SYSTEM_PROMPT,
    "comfyui": JSON_SYSTEM_PROMPT,
}

# Client connection pool for reuse (thread-safe)
import threading
_client_pool = {}
_client_pool_lock = threading.Lock()

def get_cached_client(model_id: str, provider: str = "auto"):
    """Get or create a cached API client for reuse"""
    cache_key = f"{model_id}:{provider}"
    
    with _client_pool_lock:
        if cache_key not in _client_pool:
            _client_pool[cache_key] = get_inference_client(model_id, provider)
        return _client_pool[cache_key]

# Define models and languages here to avoid importing Gradio UI
AVAILABLE_MODELS = [
    {"name": "Gemini 3.0 Pro", "id": "gemini-3.0-pro", "description": "Google Gemini 3.0 Pro via Poe with advanced reasoning"},
    {"name": "Grok 4.1 Fast", "id": "x-ai/grok-4.1-fast", "description": "Grok 4.1 Fast model via OpenRouter (20 req/min on free tier)"},
    {"name": "MiniMax M2", "id": "MiniMaxAI/MiniMax-M2", "description": "MiniMax M2 model via HuggingFace InferenceClient with Novita provider"},
    {"name": "DeepSeek V3.2-Exp", "id": "deepseek-ai/DeepSeek-V3.2-Exp", "description": "DeepSeek V3.2 Experimental via HuggingFace"},
    {"name": "DeepSeek R1", "id": "deepseek-ai/DeepSeek-R1-0528", "description": "DeepSeek R1 model for code generation"},
    {"name": "GPT-5", "id": "gpt-5", "description": "OpenAI GPT-5 via OpenRouter"},
    {"name": "GPT-5.1", "id": "gpt-5.1", "description": "OpenAI GPT-5.1 model via Poe for advanced code generation and general tasks"},
    {"name": "GPT-5.1 Instant", "id": "gpt-5.1-instant", "description": "OpenAI GPT-5.1 Instant model via Poe for fast responses"},
    {"name": "GPT-5.1 Codex", "id": "gpt-5.1-codex", "description": "OpenAI GPT-5.1 Codex model via Poe optimized for code generation"},
    {"name": "Claude-Sonnet-4.5", "id": "claude-sonnet-4.5", "description": "Anthropic Claude Sonnet 4.5 via Poe (OpenAI-compatible)"},
    {"name": "Claude-Haiku-4.5", "id": "claude-haiku-4.5", "description": "Anthropic Claude Haiku 4.5 via Poe (OpenAI-compatible)"},
    {"name": "Kimi K2 Thinking", "id": "moonshotai/Kimi-K2-Thinking", "description": "Moonshot Kimi K2 Thinking model via HuggingFace with Together AI provider"},
    {"name": "GLM-4.6", "id": "zai-org/GLM-4.6", "description": "GLM-4.6 model via HuggingFace with Cerebras provider"},
    {"name": "Gemini Flash Latest", "id": "gemini-flash-latest", "description": "Google Gemini Flash via OpenRouter"},
    {"name": "Qwen3 Max Preview", "id": "qwen3-max-preview", "description": "Qwen3 Max Preview via DashScope API"},
]

# Cache model lookup for faster access (built after AVAILABLE_MODELS is defined)
MODEL_CACHE = {model["id"]: model for model in AVAILABLE_MODELS}
print(f"[Startup] ✅ Performance optimizations loaded: {len(SYSTEM_PROMPT_CACHE)} cached prompts, {len(MODEL_CACHE)} cached models, client pooling enabled")

LANGUAGE_CHOICES = ["html", "gradio", "transformers.js", "streamlit", "comfyui", "react"]

app = FastAPI(title="AnyCoder API", version="1.0.0")

# OAuth and environment configuration (must be before CORS)
OAUTH_CLIENT_ID = os.getenv("OAUTH_CLIENT_ID", "")
OAUTH_CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET", "")
OAUTH_SCOPES = os.getenv("OAUTH_SCOPES", "openid profile manage-repos")
OPENID_PROVIDER_URL = os.getenv("OPENID_PROVIDER_URL", "https://huggingface.co")
SPACE_HOST = os.getenv("SPACE_HOST", "localhost:7860")

# Configure CORS - allow all origins in production, specific in dev
# In Docker Space, requests come from the same domain via Next.js proxy
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",") if os.getenv("ALLOWED_ORIGINS") else [
    "http://localhost:3000",
    "http://localhost:3001", 
    "http://localhost:7860",
    f"https://{SPACE_HOST}" if SPACE_HOST and not SPACE_HOST.startswith("localhost") else "http://localhost:7860"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex=r"https://.*\.hf\.space" if SPACE_HOST and not SPACE_HOST.startswith("localhost") else None,
)

# In-memory store for OAuth states (in production, use Redis or similar)
oauth_states = {}

# In-memory store for user sessions
user_sessions = {}


def is_session_expired(session_data: dict) -> bool:
    """Check if session has expired"""
    expires_at = session_data.get("expires_at")
    if not expires_at:
        # If no expiration info, check if session is older than 8 hours
        timestamp = session_data.get("timestamp", datetime.now())
        return (datetime.now() - timestamp) > timedelta(hours=8)
    
    return datetime.now() >= expires_at


# Background task for cleaning up expired sessions
async def cleanup_expired_sessions():
    """Periodically clean up expired sessions"""
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour
            
            expired_sessions = []
            for session_token, session_data in user_sessions.items():
                if is_session_expired(session_data):
                    expired_sessions.append(session_token)
            
            for session_token in expired_sessions:
                user_sessions.pop(session_token, None)
                print(f"[Auth] Cleaned up expired session: {session_token[:10]}...")
            
            if expired_sessions:
                print(f"[Auth] Cleaned up {len(expired_sessions)} expired session(s)")
        except Exception as e:
            print(f"[Auth] Cleanup error: {e}")

# Start cleanup task on app startup
@app.on_event("startup")
async def startup_event():
    """Run startup tasks"""
    asyncio.create_task(cleanup_expired_sessions())
    print("[Startup] ✅ Session cleanup task started")


# Pydantic models for request/response
class CodeGenerationRequest(BaseModel):
    query: str
    language: str = "html"
    model_id: str = "MiniMaxAI/MiniMax-M2"
    provider: str = "auto"
    history: List[List[str]] = []
    agent_mode: bool = False


class DeploymentRequest(BaseModel):
    code: str
    space_name: Optional[str] = None
    language: str
    requirements: Optional[str] = None
    existing_repo_id: Optional[str] = None  # For updating existing spaces
    commit_message: Optional[str] = None


class AuthStatus(BaseModel):
    authenticated: bool
    username: Optional[str] = None
    message: str


class ModelInfo(BaseModel):
    name: str
    id: str
    description: str


class CodeGenerationResponse(BaseModel):
    code: str
    history: List[List[str]]
    status: str


class ImportRequest(BaseModel):
    url: str
    prefer_local: bool = False


class ImportResponse(BaseModel):
    status: str
    message: str
    code: str
    language: str
    url: str
    metadata: Dict


# Mock authentication for development
# In production, integrate with HuggingFace OAuth
class MockAuth:
    def __init__(self, token: Optional[str] = None, username: Optional[str] = None):
        self.token = token
        self.username = username
    
    def is_authenticated(self):
        return bool(self.token)


def get_auth_from_header(authorization: Optional[str] = None):
    """Extract authentication from header or session token"""
    if not authorization:
        return MockAuth(None, None)
    
    # Handle "Bearer " prefix
    if authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
    else:
        token = authorization
    
    # Check if this is a session token (UUID format)
    if token and "-" in token and len(token) > 20:
        # Look up the session to get user info
        if token in user_sessions:
            session = user_sessions[token]
            return MockAuth(session["access_token"], session["username"])
    
    # Dev token format: dev_token_<username>_<timestamp>
    if token and token.startswith("dev_token_"):
        parts = token.split("_")
        username = parts[2] if len(parts) > 2 else "user"
        return MockAuth(token, username)
    
    # Regular token (OAuth access token passed directly)
    return MockAuth(token, None)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "AnyCoder API is running"}


@app.get("/api/models", response_model=List[ModelInfo])
async def get_models():
    """Get available AI models"""
    return [
        ModelInfo(
            name=model["name"],
            id=model["id"],
            description=model["description"]
        )
        for model in AVAILABLE_MODELS
    ]


@app.get("/api/languages")
async def get_languages():
    """Get available programming languages/frameworks"""
    return {"languages": LANGUAGE_CHOICES}


@app.get("/api/auth/login")
async def oauth_login(request: Request):
    """Initiate OAuth login flow"""
    # Generate a random state to prevent CSRF
    state = secrets.token_urlsafe(32)
    oauth_states[state] = {"timestamp": datetime.now()}
    
    # Build redirect URI
    protocol = "https" if SPACE_HOST and not SPACE_HOST.startswith("localhost") else "http"
    redirect_uri = f"{protocol}://{SPACE_HOST}/api/auth/callback"
    
    # Build authorization URL
    auth_url = (
        f"{OPENID_PROVIDER_URL}/oauth/authorize"
        f"?client_id={OAUTH_CLIENT_ID}"
        f"&redirect_uri={urllib.parse.quote(redirect_uri)}"
        f"&scope={urllib.parse.quote(OAUTH_SCOPES)}"
        f"&state={state}"
        f"&response_type=code"
    )
    
    return JSONResponse({"login_url": auth_url, "state": state})


@app.get("/api/auth/callback")
async def oauth_callback(code: str, state: str, request: Request):
    """Handle OAuth callback"""
    # Verify state to prevent CSRF
    if state not in oauth_states:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    # Clean up old states
    oauth_states.pop(state, None)
    
    # Exchange code for tokens
    protocol = "https" if SPACE_HOST and not SPACE_HOST.startswith("localhost") else "http"
    redirect_uri = f"{protocol}://{SPACE_HOST}/api/auth/callback"
    
    # Prepare authorization header
    auth_string = f"{OAUTH_CLIENT_ID}:{OAUTH_CLIENT_SECRET}"
    auth_bytes = auth_string.encode('utf-8')
    auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
    
    async with httpx.AsyncClient() as client:
        try:
            token_response = await client.post(
                f"{OPENID_PROVIDER_URL}/oauth/token",
                data={
                    "client_id": OAUTH_CLIENT_ID,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
                headers={
                    "Authorization": f"Basic {auth_b64}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            
            # Get user info
            access_token = token_data.get("access_token")
            userinfo_response = await client.get(
                f"{OPENID_PROVIDER_URL}/oauth/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            userinfo_response.raise_for_status()
            user_info = userinfo_response.json()
            
            # Calculate token expiration
            # OAuth tokens typically have expires_in in seconds
            expires_in = token_data.get("expires_in", 28800)  # Default 8 hours
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            # Create session
            session_token = secrets.token_urlsafe(32)
            user_sessions[session_token] = {
                "access_token": access_token,
                "user_info": user_info,
                "timestamp": datetime.now(),
                "expires_at": expires_at,
                "username": user_info.get("name") or user_info.get("preferred_username") or "user",
                "deployed_spaces": []  # Track deployed spaces for follow-up updates
            }
            
            # Redirect to frontend with session token
            frontend_url = f"{protocol}://{SPACE_HOST}/?session={session_token}"
            return RedirectResponse(url=frontend_url)
            
        except httpx.HTTPError as e:
            print(f"OAuth error: {e}")
            raise HTTPException(status_code=500, detail=f"OAuth failed: {str(e)}")


async def validate_token_with_hf(access_token: str) -> bool:
    """Validate token with HuggingFace API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{OPENID_PROVIDER_URL}/oauth/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=5.0
            )
            return response.status_code == 200
    except Exception as e:
        print(f"[Auth] Token validation error: {e}")
        return False


@app.get("/api/auth/session")
async def get_session(session: str):
    """Get user info from session token"""
    if session not in user_sessions:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    session_data = user_sessions[session]
    
    # Check if session has expired
    if is_session_expired(session_data):
        # Clean up expired session
        user_sessions.pop(session, None)
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    
    # Validate token with HuggingFace
    if not await validate_token_with_hf(session_data["access_token"]):
        # Token is invalid, clean up session
        user_sessions.pop(session, None)
        raise HTTPException(status_code=401, detail="Authentication expired. Please sign in again.")
    
    return {
        "access_token": session_data["access_token"],
        "user_info": session_data["user_info"],
    }


@app.get("/api/auth/status")
async def auth_status(authorization: Optional[str] = Header(None)):
    """Check authentication status and validate token"""
    auth = get_auth_from_header(authorization)
    
    if not auth.is_authenticated():
        return AuthStatus(
            authenticated=False,
            username=None,
            message="Not authenticated"
        )
    
    # For dev tokens, skip validation
    if auth.token and auth.token.startswith("dev_token_"):
        return AuthStatus(
            authenticated=True,
            username=auth.username,
            message=f"Authenticated as {auth.username} (dev mode)"
        )
    
    # For session tokens, check expiration and validate
    token = authorization.replace("Bearer ", "") if authorization else None
    if token and "-" in token and len(token) > 20 and token in user_sessions:
        session_data = user_sessions[token]
        
        # Check if session has expired
        if is_session_expired(session_data):
            # Clean up expired session
            user_sessions.pop(token, None)
            return AuthStatus(
                authenticated=False,
                username=None,
                message="Session expired"
            )
        
        # Validate token with HuggingFace
        if not await validate_token_with_hf(session_data["access_token"]):
            # Token is invalid, clean up session
            user_sessions.pop(token, None)
            return AuthStatus(
                authenticated=False,
                username=None,
                message="Authentication expired"
            )
        
        return AuthStatus(
            authenticated=True,
            username=auth.username,
            message=f"Authenticated as {auth.username}"
        )
    
    # For direct OAuth tokens, validate with HF
    if auth.token:
        is_valid = await validate_token_with_hf(auth.token)
        if is_valid:
            return AuthStatus(
                authenticated=True,
                username=auth.username,
                message=f"Authenticated as {auth.username}"
            )
        else:
            return AuthStatus(
                authenticated=False,
                username=None,
                message="Token expired or invalid"
            )
    
    return AuthStatus(
        authenticated=False,
        username=None,
        message="Not authenticated"
    )


def cleanup_generated_code(code: str, language: str) -> str:
    """Remove LLM explanatory text and extract only the actual code"""
    try:
        original_code = code
        
        # Special handling for transformers.js - don't clean, pass through as-is
        # The parser will handle extracting the files from === markers
        if language == "transformers.js":
            return code
        
        # Special handling for ComfyUI JSON
        if language == "comfyui":
            # Try to parse as JSON first
            try:
                json.loads(code)
                return code  # If it parses, return as-is
            except json.JSONDecodeError:
                pass
            
            # Find the last } in the code
            last_brace = code.rfind('}')
            if last_brace != -1:
                # Extract everything up to and including the last }
                potential_json = code[:last_brace + 1]
                
                # Try to find where the JSON actually starts
                json_start = 0
                if '```json' in potential_json:
                    match = re.search(r'```json\s*\n', potential_json)
                    if match:
                        json_start = match.end()
                elif '```' in potential_json:
                    match = re.search(r'```\s*\n', potential_json)
                    if match:
                        json_start = match.end()
                
                # Extract the JSON
                cleaned_json = potential_json[json_start:].strip()
                cleaned_json = re.sub(r'```\s*$', '', cleaned_json).strip()
                
                # Validate
                try:
                    json.loads(cleaned_json)
                    return cleaned_json
                except json.JSONDecodeError:
                    pass
        
        # General cleanup for code languages
        # Remove markdown code blocks and extract code
        if '```' in code:
            # Pattern to match code blocks with language specifiers
            patterns = [
                r'```(?:html|HTML)\s*\n([\s\S]+?)(?:\n```|$)',
                r'```(?:python|py|Python)\s*\n([\s\S]+?)(?:\n```|$)',
                r'```(?:javascript|js|jsx|JavaScript)\s*\n([\s\S]+?)(?:\n```|$)',
                r'```(?:typescript|ts|tsx|TypeScript)\s*\n([\s\S]+?)(?:\n```|$)',
                r'```\s*\n([\s\S]+?)(?:\n```|$)',  # Generic code block
            ]
            
            for pattern in patterns:
                match = re.search(pattern, code, re.IGNORECASE)
                if match:
                    code = match.group(1).strip()
                    break
        
        # Remove common LLM explanatory patterns
        # Remove lines that start with explanatory text
        lines = code.split('\n')
        cleaned_lines = []
        in_code = False
        
        for line in lines:
            stripped = line.strip()
            
            # Skip common explanatory patterns at the start
            if not in_code and (
                stripped.lower().startswith('here') or
                stripped.lower().startswith('this') or
                stripped.lower().startswith('the above') or
                stripped.lower().startswith('note:') or
                stripped.lower().startswith('explanation:') or
                stripped.lower().startswith('to use') or
                stripped.lower().startswith('usage:') or
                stripped.lower().startswith('instructions:') or
                stripped.startswith('===') and '===' in stripped  # Section markers
            ):
                continue
            
            # Once we hit actual code, we're in
            if stripped and not stripped.startswith('#') and not stripped.startswith('//'):
                in_code = True
            
            cleaned_lines.append(line)
        
        code = '\n'.join(cleaned_lines).strip()
        
        # Remove trailing explanatory text after the code ends
        # For HTML: remove everything after final closing tag
        if language == "html":
            # Find last </html> or </body> or </div> at root level
            last_html = code.rfind('</html>')
            last_body = code.rfind('</body>')
            last_tag = max(last_html, last_body)
            if last_tag != -1:
                # Check if there's significant text after
                after_tag = code[last_tag + 7:].strip()  # +7 for </html> length
                if after_tag and len(after_tag) > 100:  # Significant explanatory text
                    code = code[:last_tag + 7].strip()
        
        # For Python: remove text after the last function/class definition or code block
        elif language in ["gradio", "streamlit"]:
            # Find the last line that looks like actual code (not comments or blank)
            lines = code.split('\n')
            last_code_line = -1
            for i in range(len(lines) - 1, -1, -1):
                stripped = lines[i].strip()
                if stripped and not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith("'''"):
                    # This looks like actual code
                    last_code_line = i
                    break
            
            if last_code_line != -1 and last_code_line < len(lines) - 5:
                # If there are more than 5 lines after last code, likely explanatory
                code = '\n'.join(lines[:last_code_line + 1])
        
        # Return cleaned code or original if cleaning made it too short
        if len(code) > 50:
            return code
        else:
            return original_code
        
    except Exception as e:
        print(f"[Code Cleanup] Error for {language}: {e}")
        return code


@app.post("/api/generate")
async def generate_code(
    request: CodeGenerationRequest,
    authorization: Optional[str] = Header(None)
):
    """Generate code based on user query - returns streaming response"""
    # Dev mode: No authentication required - just use server's HF_TOKEN
    # In production, you would check real OAuth tokens here
    
    # Extract parameters from request body
    query = request.query
    language = request.language
    model_id = request.model_id
    provider = request.provider
    
    async def event_stream() -> AsyncGenerator[str, None]:
        """Stream generated code chunks"""
        # Use the model_id from outer scope
        selected_model_id = model_id
        
        try:
            # Fast model lookup using cache
            selected_model = MODEL_CACHE.get(selected_model_id)
            if not selected_model:
                # Fallback to first available model (shouldn't happen often)
                selected_model = AVAILABLE_MODELS[0]
                selected_model_id = selected_model["id"]
            
            # Track generated code
            generated_code = ""
            
            # Fast system prompt lookup using cache
            system_prompt = SYSTEM_PROMPT_CACHE.get(language)
            if not system_prompt:
                # Format generic prompt only if needed
                system_prompt = GENERIC_SYSTEM_PROMPT.format(language=language)
            
            # Get cached client (reuses connections)
            client = get_cached_client(selected_model_id, provider)
            
            # Get the real model ID with provider suffixes
            actual_model_id = get_real_model_id(selected_model_id)
            
            # Prepare messages (optimized - no string concatenation in hot path)
            user_content = f"Generate a {language} application: {query}"
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
            
            # Stream the response
            try:
                # Handle Mistral models with different API
                if is_mistral_model(selected_model_id):
                    print("[Generate] Using Mistral SDK")
                    stream = client.chat.stream(
                        model=actual_model_id,
                        messages=messages,
                        max_tokens=10000
                    )
                
                # All other models use OpenAI-compatible API
                else:
                    stream = client.chat.completions.create(
                        model=actual_model_id,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=10000,
                        stream=True
                    )
                
                chunk_count = 0
                is_mistral = is_mistral_model(selected_model_id)
                
                # Optimized chunk processing - reduce attribute lookups
                for chunk in stream:
                    chunk_content = None
                    
                    if is_mistral:
                        # Mistral format: chunk.data.choices[0].delta.content
                        try:
                            if chunk.data and chunk.data.choices and chunk.data.choices[0].delta.content:
                                chunk_content = chunk.data.choices[0].delta.content
                        except (AttributeError, IndexError):
                            continue
                    else:
                        # OpenAI format: chunk.choices[0].delta.content
                        try:
                            if chunk.choices and chunk.choices[0].delta.content:
                                chunk_content = chunk.choices[0].delta.content
                        except (AttributeError, IndexError):
                            continue
                    
                    if chunk_content:
                        generated_code += chunk_content
                        chunk_count += 1
                        
                        # Send chunk immediately - optimized JSON serialization
                        # Only yield control every 5 chunks to reduce overhead
                        if chunk_count % 5 == 0:
                            await asyncio.sleep(0)
                        
                        # Build event data efficiently
                        event_data = json.dumps({
                            "type": "chunk",
                            "content": chunk_content
                        })
                        yield f"data: {event_data}\n\n"
                
                # Clean up generated code (remove LLM explanatory text and markdown)
                generated_code = cleanup_generated_code(generated_code, language)
                
                # Send completion event (optimized - no timestamp in hot path)
                completion_data = json.dumps({
                    "type": "complete",
                    "code": generated_code
                })
                yield f"data: {completion_data}\n\n"
                
            except Exception as e:
                # Handle rate limiting and other API errors
                error_message = str(e)
                is_rate_limit = False
                error_type = type(e).__name__
                
                # Check for OpenAI SDK rate limit errors
                if error_type == "RateLimitError" or "rate_limit" in error_type.lower():
                    is_rate_limit = True
                # Check if this is a rate limit error (429 status code)
                elif hasattr(e, 'status_code') and e.status_code == 429:
                    is_rate_limit = True
                # Check error message for rate limit indicators
                elif "429" in error_message or "rate limit" in error_message.lower() or "too many requests" in error_message.lower():
                    is_rate_limit = True
                
                if is_rate_limit:
                    # Try to extract retry-after header or message
                    retry_after = None
                    if hasattr(e, 'response') and e.response:
                        retry_after = e.response.headers.get('Retry-After') or e.response.headers.get('retry-after')
                    # Also check if the error object has retry_after
                    elif hasattr(e, 'retry_after'):
                        retry_after = str(e.retry_after)
                    
                    if selected_model_id == "x-ai/grok-4.1-fast" or selected_model_id.startswith("openrouter/"):
                        error_message = "⏱️ Rate limit exceeded for OpenRouter model"
                        if retry_after:
                            error_message += f". Please wait {retry_after} seconds before trying again."
                        else:
                            error_message += ". Free tier allows up to 20 requests per minute. Please wait a moment and try again."
                    else:
                        error_message = f"⏱️ Rate limit exceeded. Please wait before trying again."
                        if retry_after:
                            error_message += f" Retry after {retry_after} seconds."
                
                # Check for other common API errors
                elif hasattr(e, 'status_code'):
                    if e.status_code == 401:
                        error_message = "❌ Authentication failed. Please check your API key."
                    elif e.status_code == 403:
                        error_message = "❌ Access forbidden. Please check your API key permissions."
                    elif e.status_code == 500 or e.status_code == 502 or e.status_code == 503:
                        error_message = "❌ Service temporarily unavailable. Please try again later."
                
                error_data = json.dumps({
                    "type": "error",
                    "message": error_message
                })
                yield f"data: {error_data}\n\n"
                
        except Exception as e:
            # Fallback error handling
            error_message = str(e)
            # Check if it's a rate limit error in the exception message
            if "429" in error_message or "rate limit" in error_message.lower() or "too many requests" in error_message.lower():
                if selected_model_id == "x-ai/grok-4.1-fast" or selected_model_id.startswith("openrouter/"):
                    error_message = "⏱️ Rate limit exceeded for OpenRouter model. Free tier allows up to 20 requests per minute. Please wait a moment and try again."
                else:
                    error_message = "⏱️ Rate limit exceeded. Please wait before trying again."
            
            error_data = json.dumps({
                "type": "error",
                "message": f"Generation error: {error_message}"
            })
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Encoding": "none",
            "Transfer-Encoding": "chunked"
        }
    )


@app.post("/api/deploy")
async def deploy(
    request: DeploymentRequest,
    authorization: Optional[str] = Header(None)
):
    """Deploy generated code to HuggingFace Spaces"""
    auth = get_auth_from_header(authorization)
    
    if not auth.is_authenticated():
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Check if this is dev mode (no real token)
    if auth.token and auth.token.startswith("dev_token_"):
        # In dev mode, open HF Spaces creation page
        from backend_deploy import detect_sdk_from_code
        base_url = "https://huggingface.co/new-space"
        
        sdk = detect_sdk_from_code(request.code, request.language)
        
        params = urllib.parse.urlencode({
            "name": request.space_name or "my-anycoder-app",
            "sdk": sdk
        })
        
        # Prepare file content based on language
        if request.language in ["html", "transformers.js", "comfyui"]:
            file_path = "index.html"
        else:
            file_path = "app.py"
        
        files_params = urllib.parse.urlencode({
            "files[0][path]": file_path,
            "files[0][content]": request.code
        })
        
        space_url = f"{base_url}?{params}&{files_params}"
        
        return {
            "success": True,
            "space_url": space_url,
            "message": "Dev mode: Please create the space manually",
            "dev_mode": True
        }
    
    # Production mode with real OAuth token
    try:
        from backend_deploy import deploy_to_huggingface_space
        
        # Get user token - should be the access_token from OAuth session
        user_token = auth.token if auth.token else os.getenv("HF_TOKEN")
        
        if not user_token:
            raise HTTPException(status_code=401, detail="No HuggingFace token available. Please sign in first.")
        
        print(f"[Deploy] Attempting deployment with token (first 10 chars): {user_token[:10]}...")
        print(f"[Deploy] Request parameters - language: {request.language}, space_name: {request.space_name}, existing_repo_id: {request.existing_repo_id}")
        
        # Check for existing deployed space in this session
        existing_repo_id = request.existing_repo_id
        session_token = authorization.replace("Bearer ", "") if authorization else None
        
        # If no existing_repo_id provided, check session for previously deployed spaces
        if not existing_repo_id and session_token and session_token in user_sessions:
            session = user_sessions[session_token]
            deployed_spaces = session.get("deployed_spaces", [])
            
            # Find the most recent space for this language
            for space in reversed(deployed_spaces):
                if space.get("language") == request.language:
                    existing_repo_id = space.get("repo_id")
                    print(f"[Deploy] Found existing space for {request.language}: {existing_repo_id}")
                    break
        
        # Use the standalone deployment function
        print(f"[Deploy] Calling deploy_to_huggingface_space with existing_repo_id: {existing_repo_id}")
        success, message, space_url = deploy_to_huggingface_space(
            code=request.code,
            language=request.language,
            space_name=request.space_name,
            token=user_token,
            username=auth.username,
            description=request.description if hasattr(request, 'description') else None,
            private=False,
            existing_repo_id=existing_repo_id,
            commit_message=request.commit_message
        )
        
        if success:
            # Extract repo_id from space_url
            repo_id = space_url.split("/spaces/")[-1] if space_url else None
            print(f"[Deploy] Success! Repo ID: {repo_id}")
            
            # Track deployed space in session for follow-up updates
            if session_token and session_token in user_sessions:
                if repo_id:
                    session = user_sessions[session_token]
                    deployed_spaces = session.get("deployed_spaces", [])
                    
                    # Update or add the space
                    space_entry = {
                        "repo_id": repo_id,
                        "language": request.language,
                        "timestamp": datetime.now()
                    }
                    
                    # Remove old entry for same repo_id if exists
                    deployed_spaces = [s for s in deployed_spaces if s.get("repo_id") != repo_id]
                    deployed_spaces.append(space_entry)
                    
                    session["deployed_spaces"] = deployed_spaces
                    print(f"[Deploy] Tracked space in session: {repo_id}")
            
            return {
                "success": True,
                "space_url": space_url,
                "message": message,
                "repo_id": repo_id
            }
        else:
            # Provide user-friendly error message based on the error
            if "401" in message or "Unauthorized" in message:
                raise HTTPException(
                    status_code=401, 
                    detail="Authentication failed. Please sign in again with HuggingFace."
                )
            elif "403" in message or "Forbidden" in message or "Permission" in message:
                raise HTTPException(
                    status_code=403, 
                    detail="Permission denied. Your HuggingFace token may not have the required permissions (manage-repos scope)."
                )
            else:
                raise HTTPException(
                    status_code=500, 
                    detail=message
                )
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Log the full error for debugging
        import traceback
        error_details = traceback.format_exc()
        print(f"[Deploy] Deployment error: {error_details}")
        
        raise HTTPException(
            status_code=500, 
            detail=f"Deployment failed: {str(e)}"
        )


@app.post("/api/import", response_model=ImportResponse)
async def import_project(request: ImportRequest):
    """
    Import a project from HuggingFace Space, HuggingFace Model, or GitHub repo
    
    Supports URLs like:
    - https://huggingface.co/spaces/username/space-name
    - https://huggingface.co/username/model-name
    - https://github.com/username/repo-name
    """
    try:
        importer = ProjectImporter()
        result = importer.import_from_url(request.url)
        
        # Handle model-specific prefer_local flag
        if request.prefer_local and result.get('metadata', {}).get('has_alternatives'):
            # Switch to local code if available
            local_code = result['metadata'].get('local_code')
            if local_code:
                result['code'] = local_code
                result['metadata']['code_type'] = 'local'
                result['message'] = result['message'].replace('inference', 'local')
        
        return ImportResponse(**result)
    
    except Exception as e:
        return ImportResponse(
            status="error",
            message=f"Import failed: {str(e)}",
            code="",
            language="unknown",
            url=request.url,
            metadata={}
        )


@app.get("/api/import/space/{username}/{space_name}")
async def import_space(username: str, space_name: str):
    """Import a specific HuggingFace Space by username and space name"""
    try:
        importer = ProjectImporter()
        result = importer.import_space(username, space_name)
        return result
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to import space: {str(e)}",
            "code": "",
            "language": "unknown",
            "url": f"https://huggingface.co/spaces/{username}/{space_name}",
            "metadata": {}
        }


@app.get("/api/import/model/{path:path}")
async def import_model(path: str, prefer_local: bool = False):
    """
    Import a specific HuggingFace Model by model ID
    
    Example: /api/import/model/meta-llama/Llama-3.2-1B-Instruct
    """
    try:
        importer = ProjectImporter()
        result = importer.import_model(path, prefer_local=prefer_local)
        return result
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to import model: {str(e)}",
            "code": "",
            "language": "python",
            "url": f"https://huggingface.co/{path}",
            "metadata": {}
        }


@app.get("/api/import/github/{owner}/{repo}")
async def import_github(owner: str, repo: str):
    """Import a GitHub repository by owner and repo name"""
    try:
        importer = ProjectImporter()
        result = importer.import_github_repo(owner, repo)
        return result
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to import repository: {str(e)}",
            "code": "",
            "language": "python",
            "url": f"https://github.com/{owner}/{repo}",
            "metadata": {}
        }


@app.websocket("/ws/generate")
async def websocket_generate(websocket: WebSocket):
    """WebSocket endpoint for real-time code generation"""
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            query = data.get("query")
            language = data.get("language", "html")
            model_id = data.get("model_id", "MiniMaxAI/MiniMax-M2")
            
            # Send acknowledgment
            await websocket.send_json({
                "type": "status",
                "message": "Generating code..."
            })
            
            # Mock code generation for now
            await asyncio.sleep(0.5)
            
            # Send generated code in chunks
            sample_code = f"<!-- Generated {language} code -->\n<h1>Hello from AnyCoder!</h1>"
            
            for i, char in enumerate(sample_code):
                await websocket.send_json({
                    "type": "chunk",
                    "content": char,
                    "progress": (i + 1) / len(sample_code) * 100
                })
                await asyncio.sleep(0.01)
            
            # Send completion
            await websocket.send_json({
                "type": "complete",
                "code": sample_code
            })
            
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
        await websocket.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend_api:app", host="0.0.0.0", port=8000, reload=True)

