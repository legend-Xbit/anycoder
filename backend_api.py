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
        REACT_FOLLOW_UP_SYSTEM_PROMPT,  # Import React followup prompt
        get_gradio_system_prompt,  # Import the function to get dynamic prompt
        get_comfyui_system_prompt,  # Import the function to get dynamic ComfyUI prompt
        JSON_SYSTEM_PROMPT,
        DAGGR_SYSTEM_PROMPT,
        GENERIC_SYSTEM_PROMPT
    )
    # Get the Gradio system prompt (includes full Gradio 6 documentation)
    GRADIO_SYSTEM_PROMPT = get_gradio_system_prompt()
    # Get the ComfyUI system prompt (includes full ComfyUI documentation)
    COMFYUI_SYSTEM_PROMPT = get_comfyui_system_prompt()
    print("[Startup] ✅ All system prompts loaded successfully from backend_prompts.py")
    print(f"[Startup] 📚 Gradio system prompt loaded with full documentation ({len(GRADIO_SYSTEM_PROMPT)} chars)")
    print(f"[Startup] 📚 ComfyUI system prompt loaded with full documentation ({len(COMFYUI_SYSTEM_PROMPT)} chars)")
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
    COMFYUI_SYSTEM_PROMPT = "You are an expert ComfyUI developer. Generate clean, valid JSON workflows for ComfyUI based on the user's request. READ THE USER'S REQUEST CAREFULLY and create a workflow that matches their specific needs."
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
    "comfyui": COMFYUI_SYSTEM_PROMPT,  # Use ComfyUI-specific prompt with documentation
    "daggr": DAGGR_SYSTEM_PROMPT,
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
    {"name": "Kimi-K2.5 🧠", "id": "moonshotai/Kimi-K2.5", "description": "Kimi-K2.5 - New powerful reasoning model via HuggingFace Router with Novita provider (Default)", "supports_images": True},
    {"name": "GLM-4.7-Flash ⚡", "id": "zai-org/GLM-4.7-Flash", "description": "GLM-4.7-Flash - Ultra-fast GLM model via HuggingFace Router with Novita provider", "supports_images": False},
    {"name": "GLM-4.7", "id": "zai-org/GLM-4.7", "description": "GLM-4.7 - Latest GLM model via HuggingFace Router with Cerebras provider", "supports_images": False},
    {"name": "MiniMax M2.1", "id": "MiniMaxAI/MiniMax-M2.1", "description": "MiniMax M2.1 - Enhanced model via HuggingFace Router", "supports_images": False},
    {"name": "GLM-4.6", "id": "zai-org/GLM-4.6", "description": "GLM-4.6 model via HuggingFace with Cerebras provider", "supports_images": False},
    {"name": "GLM-4.6V 👁️", "id": "zai-org/GLM-4.6V:zai-org", "description": "GLM-4.6V vision model - supports image uploads for visual understanding", "supports_images": True},
    {"name": "DeepSeek V3", "id": "deepseek-ai/DeepSeek-V3", "description": "DeepSeek V3 - Fast model for code generation via HuggingFace Router with Novita provider", "supports_images": False},
    {"name": "DeepSeek R1", "id": "deepseek-ai/DeepSeek-R1", "description": "DeepSeek R1 model for code generation via HuggingFace", "supports_images": False},
    {"name": "MiniMax M2", "id": "MiniMaxAI/MiniMax-M2", "description": "MiniMax M2 model via HuggingFace InferenceClient with Novita provider", "supports_images": False},
    {"name": "Kimi K2 Thinking", "id": "moonshotai/Kimi-K2-Thinking", "description": "Moonshot Kimi K2 Thinking model via HuggingFace with Together AI provider", "supports_images": False},
]

# Cache model lookup for faster access (built after AVAILABLE_MODELS is defined)
MODEL_CACHE = {model["id"]: model for model in AVAILABLE_MODELS}
print(f"[Startup] ✅ Performance optimizations loaded: {len(SYSTEM_PROMPT_CACHE)} cached prompts, {len(MODEL_CACHE)} cached models, client pooling enabled")

LANGUAGE_CHOICES = ["html", "gradio", "transformers.js", "streamlit", "comfyui", "react", "daggr"]

app = FastAPI(title="AnyCoder API", version="1.0.0")

# OAuth and environment configuration (must be before CORS)
OAUTH_CLIENT_ID = os.getenv("OAUTH_CLIENT_ID", "")
OAUTH_CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET", "")
OAUTH_SCOPES = os.getenv("OAUTH_SCOPES", "openid profile manage-repos write-discussions")
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
    model_id: str = "moonshotai/Kimi-K2.5"
    provider: str = "auto"
    history: List[List[str]] = []
    agent_mode: bool = False
    existing_repo_id: Optional[str] = None  # For auto-deploy to update existing space
    skip_auto_deploy: bool = False  # Skip auto-deploy (for PR creation)
    image_url: Optional[str] = None  # For vision models like GLM-4.6V


class DeploymentRequest(BaseModel):
    code: str
    space_name: Optional[str] = None
    language: str
    requirements: Optional[str] = None
    existing_repo_id: Optional[str] = None  # For updating existing spaces
    commit_message: Optional[str] = None
    history: List[Dict] = []  # Chat history for tracking deployed spaces


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
    username: Optional[str] = None  # Username of authenticated user for ownership check


class ImportResponse(BaseModel):
    status: str
    message: str
    code: str
    language: str
    url: str
    metadata: Dict
    owned_by_user: bool = False  # True if user owns the imported repo
    repo_id: Optional[str] = None  # The repo ID (username/repo-name) if applicable


class PullRequestRequest(BaseModel):
    repo_id: str  # username/space-name
    code: str
    language: str
    pr_title: Optional[str] = None
    pr_description: Optional[str] = None


class PullRequestResponse(BaseModel):
    success: bool
    message: str
    pr_url: Optional[str] = None


class DuplicateSpaceRequest(BaseModel):
    from_space_id: str  # username/space-name
    to_space_name: Optional[str] = None  # Just the name, not full ID
    private: bool = False


class DuplicateSpaceResponse(BaseModel):
    success: bool
    message: str
    space_url: Optional[str] = None
    space_id: Optional[str] = None


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
            username = session.get("username")
            
            # If username is missing from session (e.g., old session), try to fetch it
            if not username and session.get("user_info"):
                user_info = session["user_info"]
                # Use same order as OAuth callback for consistency
                username = (
                    user_info.get("preferred_username") or
                    user_info.get("name") or
                    user_info.get("sub") or
                    user_info.get("username") or
                    "user"
                )
                # Update the session with the username for future requests
                session["username"] = username
                print(f"[Auth] Extracted and cached username from user_info: {username}")
            
            return MockAuth(session["access_token"], username)
    
    # Dev token format: dev_token_<username>_<timestamp>
    if token and token.startswith("dev_token_"):
        parts = token.split("_")
        username = parts[2] if len(parts) > 2 else "user"
        return MockAuth(token, username)
    
    # Regular OAuth access token passed directly - try to fetch username from HF
    # This happens when frontend sends OAuth token after OAuth callback
    if token and len(token) > 20:
        try:
            from huggingface_hub import HfApi
            hf_api = HfApi(token=token)
            user_info = hf_api.whoami()
            username = (
                user_info.get("preferred_username") or
                user_info.get("name") or
                user_info.get("sub") or
                "user"
            )
            print(f"[Auth] Fetched username from OAuth token: {username}")
            return MockAuth(token, username)
        except Exception as e:
            print(f"[Auth] Could not fetch username from OAuth token: {e}")
            # Return with token but no username - deployment will try to fetch it
            return MockAuth(token, None)
    
    # Fallback: token with no username
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
            
            # Extract username - try multiple possible fields
            username = (
                user_info.get("preferred_username") or  # Primary HF field
                user_info.get("name") or                # Alternative field
                user_info.get("sub") or                 # OpenID subject
                user_info.get("username") or            # Generic username
                "user"                                  # Fallback
            )
            
            print(f"[OAuth] User info received: {user_info}")
            print(f"[OAuth] Extracted username: {username}")
            
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
                "username": username,
                "deployed_spaces": []  # Track deployed spaces for follow-up updates
            }
            
            print(f"[OAuth] Session created: {session_token[:10]}... for user: {username}")
            
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
        elif language in ["gradio", "streamlit", "daggr"]:
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


def extract_reasoning(code: str, language: str) -> str:
    """Extract LLM reasoning/explanatory text that's outside the main code block"""
    try:
        if not code:
            return ""
        
        # 1. Check for <think> tags (e.g. from DeepSeek-R1 or newer GLM-4)
        think_match = re.search(r'<think>([\s\S]*?)</think>', code, re.IGNORECASE)
        if think_match:
            return think_match.group(1).strip()
            
        # 2. Extract everything outside of markdown code blocks
        blocks = list(re.finditer(r'```(?:[\w]*)\s*\n([\s\S]*?)(?:\n```|$)', code, re.IGNORECASE))
        
        if not blocks:
            return ""
            
        text_parts = []
        last_end = 0
        for match in blocks:
            pre_text = code[last_end:match.start()].strip()
            if pre_text and len(pre_text) > 10:
                text_parts.append(pre_text)
            last_end = match.end()
            
        post_text = code[last_end:].strip()
        if post_text and len(post_text) > 10:
            text_parts.append(post_text)
            
        return "\n\n".join(text_parts).strip()
    except Exception as e:
        print(f"[Reasoning Extraction] Error: {e}")
        return ""


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
            
            # Detect if this is a followup request for React apps
            # Check if there's existing code in the conversation history
            is_followup = False
            if language == "react" and request.history:
                # Check if there's any previous assistant message with code (indicating a followup)
                for msg in request.history:
                    if isinstance(msg, dict):
                        role = msg.get('role', '')
                        content = msg.get('content', '')
                    elif isinstance(msg, list) and len(msg) >= 2:
                        role = msg[0]
                        content = msg[1]
                    else:
                        continue
                    
                    # If we find previous code from assistant, this is a followup
                    if role == 'assistant' and ('===' in content or 'Dockerfile' in content or 'package.json' in content):
                        is_followup = True
                        print(f"[Generate] Detected React followup request")
                        break
            
            # Use followup prompt for React if detected
            if is_followup and language == "react":
                system_prompt = REACT_FOLLOW_UP_SYSTEM_PROMPT
                print(f"[Generate] Using React followup system prompt for targeted fixes")
            
            # Get cached client (reuses connections)
            client = get_cached_client(selected_model_id, provider)
            
            # Get the real model ID with provider suffixes
            actual_model_id = get_real_model_id(selected_model_id)
            
            # Prepare messages (optimized - no string concatenation in hot path)
            # Check if this is a vision model and we have an image
            if request.image_url and selected_model_id == "zai-org/GLM-4.6V:zai-org":
                # Vision model with image - use multi-modal format
                user_content = [
                    {
                        "type": "text",
                        "text": f"Generate a {language} application: {query}"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": request.image_url
                        }
                    }
                ]
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ]
            else:
                # Regular text-only model
                user_content = f"Generate a {language} application: {query}"
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ]
            
            # Stream the response
            try:
                # All models now use OpenAI-compatible API via HF Router or Inference API
                stream = client.chat.completions.create(
                    model=actual_model_id,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=10000,
                    stream=True
                )
                
                chunk_count = 0
                
                # Only process stream if it exists
                if stream:
                    # Optimized chunk processing
                    for chunk in stream:
                        chunk_content = None
                        
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
                
                # Extract reasoning before cleaning up
                reasoning = extract_reasoning(generated_code, language)
                
                # Clean up generated code (remove LLM explanatory text and markdown)
                generated_code = cleanup_generated_code(generated_code, language)
                
                # Send completion event (include reasoning for GLM-4.7)
                completion_dict = {
                    "type": "complete",
                    "code": generated_code
                }
                if selected_model_id == "zai-org/GLM-4.7" and reasoning:
                    completion_dict["reasoning"] = reasoning
                    
                completion_data = json.dumps(completion_dict)
                yield f"data: {completion_data}\n\n"
                
                # Auto-deploy after code generation (if authenticated and not skipped)
                auth = get_auth_from_header(authorization)
                
                if request.skip_auto_deploy:
                    print(f"[Auto-Deploy] Skipped - PR creation will be handled by frontend")
                
                if auth.is_authenticated() and not (auth.token and auth.token.startswith("dev_token_")) and not request.skip_auto_deploy:
                    try:
                        # Send deploying status
                        deploying_data = json.dumps({
                            "type": "deploying",
                            "message": "🚀 Deploying your app to HuggingFace Spaces..."
                        })
                        yield f"data: {deploying_data}\n\n"
                        
                        # Import deployment function
                        from backend_deploy import deploy_to_huggingface_space
                        
                        # Convert history to the format expected by deploy function
                        # History comes from frontend as [[role, content], ...]
                        history_list = []
                        if request.history:
                            for msg in request.history:
                                if isinstance(msg, list) and len(msg) >= 2:
                                    # Already in correct format [[role, content], ...]
                                    history_list.append([msg[0], msg[1]])
                                elif isinstance(msg, dict):
                                    # Convert dict format to list format
                                    role = msg.get('role', '')
                                    content = msg.get('content', '')
                                    if role and content:
                                        history_list.append([role, content])
                        
                        print(f"[Auto-Deploy] Starting deployment...")
                        print(f"[Auto-Deploy] - Language: {language}")
                        print(f"[Auto-Deploy] - History items: {len(history_list)}")
                        print(f"[Auto-Deploy] - Username: {auth.username}")
                        print(f"[Auto-Deploy] - Code length: {len(generated_code)}")
                        print(f"[Auto-Deploy] - Existing repo ID from request: {request.existing_repo_id}")
                        
                        # Deploy the code (update existing space if provided)
                        success, message, space_url = deploy_to_huggingface_space(
                            code=generated_code,
                            language=language,
                            token=auth.token,
                            username=auth.username,
                            existing_repo_id=request.existing_repo_id,  # Use duplicated/imported space
                            history=history_list
                        )
                        
                        print(f"[Auto-Deploy] Deployment result:")
                        print(f"[Auto-Deploy] - Success: {success}")
                        print(f"[Auto-Deploy] - Message: {message}")
                        print(f"[Auto-Deploy] - Space URL: {space_url}")
                        
                        if success and space_url:
                            # Send deployment success
                            deploy_success_data = json.dumps({
                                "type": "deployed",
                                "message": message,
                                "space_url": space_url
                            })
                            yield f"data: {deploy_success_data}\n\n"
                        else:
                            # Send deployment error (non-blocking - code generation still succeeded)
                            deploy_error_data = json.dumps({
                                "type": "deploy_error",
                                "message": f"⚠️ Deployment failed: {message}"
                            })
                            yield f"data: {deploy_error_data}\n\n"
                    except Exception as deploy_error:
                        # Log deployment error but don't fail the generation
                        import traceback
                        print(f"[Auto-Deploy] ========== DEPLOYMENT EXCEPTION ==========")
                        print(f"[Auto-Deploy] Exception type: {type(deploy_error).__name__}")
                        print(f"[Auto-Deploy] Error message: {str(deploy_error)}")
                        print(f"[Auto-Deploy] Full traceback:")
                        traceback.print_exc()
                        print(f"[Auto-Deploy] ==========================================")
                        
                        deploy_error_data = json.dumps({
                            "type": "deploy_error",
                            "message": f"⚠️ Deployment error: {str(deploy_error)}"
                        })
                        yield f"data: {deploy_error_data}\n\n"
                else:
                    print(f"[Auto-Deploy] Skipped - authenticated: {auth.is_authenticated()}, token_exists: {auth.token is not None}, is_dev: {auth.token.startswith('dev_token_') if auth.token else False}")
                
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
    print(f"[Deploy] ========== NEW DEPLOYMENT REQUEST ==========")
    print(f"[Deploy] Authorization header present: {authorization is not None}")
    if authorization:
        auth_preview = authorization[:20] + "..." if len(authorization) > 20 else authorization
        print(f"[Deploy] Authorization preview: {auth_preview}")
    
    auth = get_auth_from_header(authorization)
    
    print(f"[Deploy] Auth object - is_authenticated: {auth.is_authenticated()}, username: {auth.username}, has_token: {auth.token is not None}")
    
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
        
        # If username is missing, fetch it from HuggingFace API
        username = auth.username
        if not username:
            print(f"[Deploy] Username not found in auth, fetching from HuggingFace API...")
            try:
                from huggingface_hub import HfApi
                hf_api = HfApi(token=user_token)
                user_info = hf_api.whoami()
                username = user_info.get("name") or user_info.get("preferred_username") or "user"
                print(f"[Deploy] Fetched username from HF API: {username}")
            except Exception as e:
                print(f"[Deploy] Warning: Could not fetch username from HF API: {e}")
                # Continue without username - the deploy function will try to fetch it again
        
        # Check for existing deployed space in this session
        session_token = authorization.replace("Bearer ", "") if authorization else None
        existing_repo_id = request.existing_repo_id
        
        # PRIORITY 1: Check history for deployed/imported spaces (like Gradio version does)
        # This is more reliable than session tracking since history persists in frontend
        if request.history and username:
            print(f"[Deploy] ========== CHECKING HISTORY ==========")
            print(f"[Deploy] History length: {len(request.history)} messages")
            print(f"[Deploy] Username: {username}")
            
            # Log each message in history for debugging
            for i, msg in enumerate(request.history):
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                content_preview = content[:100] if content else ''
                print(f"[Deploy]   Message {i+1}: role={role}, content_preview='{content_preview}...'")
            
            print(f"[Deploy] ==========================================")
            
            for msg in request.history:
                role = msg.get('role', '')
                content = msg.get('content', '')
                
                # Check for deployment confirmations
                if role == 'assistant' and ('✅ Deployed!' in content or '✅ Updated!' in content):
                    import re
                    print(f"[Deploy] 🔍 Found deployment message in history!")
                    print(f"[Deploy] Content: {content[:200]}")
                    match = re.search(r'huggingface\.co/spaces/([^/\s\)]+/[^/\s\)]+)', content)
                    if match:
                        history_space_id = match.group(1)
                        print(f"[Deploy] ✅ EXTRACTED space ID from history: {history_space_id}")
                        if not existing_repo_id:
                            existing_repo_id = history_space_id
                            print(f"[Deploy] ✅ WILL UPDATE EXISTING SPACE: {existing_repo_id}")
                        break
                    else:
                        print(f"[Deploy] ⚠️ Deployment message found but couldn't extract space ID")
                
                # Check for imports
                elif role == 'user' and 'import' in content.lower():
                    import re
                    match = re.search(r'huggingface\.co/spaces/([^/\s\)]+/[^/\s\)]+)', content)
                    if match:
                        imported_space = match.group(1)
                        # Only use if user owns it
                        if imported_space.startswith(f"{username}/"):
                            print(f"[Deploy] ✅ Found imported space in history (user owns it): {imported_space}")
                            if not existing_repo_id:
                                existing_repo_id = imported_space
                            break
        else:
            if not request.history:
                print(f"[Deploy] ⚠️ No history provided in request")
            if not username:
                print(f"[Deploy] ⚠️ No username available")
        
        # PRIORITY 2: Check session for previously deployed spaces (fallback)
        # This helps when history isn't passed from frontend
        if not existing_repo_id and session_token and session_token in user_sessions:
            session = user_sessions[session_token]
            
            # Ensure deployed_spaces exists (for backward compatibility with old sessions)
            if "deployed_spaces" not in session:
                session["deployed_spaces"] = []
            
            deployed_spaces = session.get("deployed_spaces", [])
            
            print(f"[Deploy] Checking session for existing spaces. Found {len(deployed_spaces)} deployed spaces.")
            for i, space in enumerate(deployed_spaces):
                print(f"[Deploy]   Space {i+1}: repo_id={space.get('repo_id')}, language={space.get('language')}, timestamp={space.get('timestamp')}")
            
            # Find the most recent space for this language
            for space in reversed(deployed_spaces):
                if space.get("language") == request.language:
                    session_space_id = space.get("repo_id")
                    print(f"[Deploy] ✅ Found existing space in session for {request.language}: {session_space_id}")
                    existing_repo_id = session_space_id
                    break
            
            if not existing_repo_id:
                print(f"[Deploy] ⚠️ No existing space found for language: {request.language}")
        elif not existing_repo_id:
            print(f"[Deploy] ⚠️ No session found and no history provided. session_token: {session_token[:10] if session_token else 'None'}")
        
        # Use the standalone deployment function
        print(f"[Deploy] ========== CALLING deploy_to_huggingface_space ==========")
        print(f"[Deploy] existing_repo_id: {existing_repo_id}")
        print(f"[Deploy] space_name: {request.space_name}")
        print(f"[Deploy] language: {request.language}")
        print(f"[Deploy] username: {username}")
        print(f"[Deploy] ==========================================================")
        
        success, message, space_url = deploy_to_huggingface_space(
            code=request.code,
            language=request.language,
            space_name=request.space_name,
            token=user_token,
            username=username,
            description=request.description if hasattr(request, 'description') else None,
            private=False,
            existing_repo_id=existing_repo_id,
            commit_message=request.commit_message
        )
        
        if success:
            # Extract repo_id from space_url
            repo_id = space_url.split("/spaces/")[-1] if space_url else None
            print(f"[Deploy] ✅ Success! Repo ID: {repo_id}")
            print(f"[Deploy] Space URL: {space_url}")
            print(f"[Deploy] Message: {message}")
            
            # Track deployed space in session for follow-up updates
            if session_token and session_token in user_sessions:
                if repo_id:
                    session = user_sessions[session_token]
                    
                    # Ensure deployed_spaces exists
                    if "deployed_spaces" not in session:
                        session["deployed_spaces"] = []
                    
                    deployed_spaces = session.get("deployed_spaces", [])
                    
                    print(f"[Deploy] 📝 Tracking space in session...")
                    print(f"[Deploy] Current deployed_spaces count: {len(deployed_spaces)}")
                    
                    # Update or add the space
                    space_entry = {
                        "repo_id": repo_id,
                        "language": request.language,
                        "timestamp": datetime.now()
                    }
                    
                    # Remove old entry for same repo_id if exists
                    old_count = len(deployed_spaces)
                    deployed_spaces = [s for s in deployed_spaces if s.get("repo_id") != repo_id]
                    if old_count != len(deployed_spaces):
                        print(f"[Deploy] Removed old entry for {repo_id}")
                    
                    # Also remove old entries for same language (keep only most recent per language)
                    # This ensures we always update the same space for a given language
                    deployed_spaces = [s for s in deployed_spaces if s.get("language") != request.language]
                    
                    deployed_spaces.append(space_entry)
                    
                    session["deployed_spaces"] = deployed_spaces
                    print(f"[Deploy] ✅ Tracked space in session: {repo_id}")
                    print(f"[Deploy] New deployed_spaces count: {len(deployed_spaces)}")
                    print(f"[Deploy] All deployed spaces: {[s.get('repo_id') for s in deployed_spaces]}")
                else:
                    print(f"[Deploy] ⚠️ Could not extract repo_id from space_url: {space_url}")
            else:
                if not session_token:
                    print(f"[Deploy] ⚠️ No session_token provided for tracking")
                elif session_token not in user_sessions:
                    print(f"[Deploy] ⚠️ Session not found: {session_token[:10]}...")
                    print(f"[Deploy] Available sessions: {[k[:10] for k in list(user_sessions.keys())[:5]]}")
            
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


@app.post("/api/create-pr", response_model=PullRequestResponse)
async def create_pull_request(
    request: PullRequestRequest,
    authorization: Optional[str] = Header(None)
):
    """Create a Pull Request on an existing HuggingFace Space with redesigned code"""
    print(f"[PR] ========== NEW PULL REQUEST ==========")
    print(f"[PR] Repo ID: {request.repo_id}")
    print(f"[PR] Language: {request.language}")
    print(f"[PR] PR Title: {request.pr_title}")
    
    auth = get_auth_from_header(authorization)
    
    if not auth.is_authenticated():
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Check if this is dev mode
    if auth.token and auth.token.startswith("dev_token_"):
        return PullRequestResponse(
            success=False,
            message="Dev mode: PR creation not available in dev mode. Please use production authentication.",
            pr_url=None
        )
    
    # Production mode with real OAuth token
    try:
        from backend_deploy import create_pull_request_on_space
        
        user_token = auth.token if auth.token else os.getenv("HF_TOKEN")
        
        if not user_token:
            raise HTTPException(status_code=401, detail="No HuggingFace token available. Please sign in first.")
        
        print(f"[PR] Creating PR with token (first 10 chars): {user_token[:10]}...")
        
        # Create the pull request
        success, message, pr_url = create_pull_request_on_space(
            repo_id=request.repo_id,
            code=request.code,
            language=request.language,
            token=user_token,
            pr_title=request.pr_title,
            pr_description=request.pr_description
        )
        
        print(f"[PR] Result:")
        print(f"[PR] - Success: {success}")
        print(f"[PR] - Message: {message}")
        print(f"[PR] - PR URL: {pr_url}")
        
        if success:
            return PullRequestResponse(
                success=True,
                message=message,
                pr_url=pr_url
            )
        else:
            # Provide user-friendly error messages
            if "401" in message or "Unauthorized" in message:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication failed. Please sign in again with HuggingFace."
                )
            elif "403" in message or "Forbidden" in message or "Permission" in message:
                raise HTTPException(
                    status_code=403,
                    detail="Permission denied. You may not have write access to this space."
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=message
                )
                
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"[PR] Error: {error_details}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create pull request: {str(e)}"
        )


@app.post("/api/duplicate-space", response_model=DuplicateSpaceResponse)
async def duplicate_space_endpoint(
    request: DuplicateSpaceRequest,
    authorization: Optional[str] = Header(None)
):
    """Duplicate a HuggingFace Space to the user's account"""
    print(f"[Duplicate] ========== DUPLICATE SPACE REQUEST ==========")
    print(f"[Duplicate] From: {request.from_space_id}")
    print(f"[Duplicate] To: {request.to_space_name or 'auto'}")
    print(f"[Duplicate] Private: {request.private}")
    
    auth = get_auth_from_header(authorization)
    
    if not auth.is_authenticated():
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Check if this is dev mode
    if auth.token and auth.token.startswith("dev_token_"):
        return DuplicateSpaceResponse(
            success=False,
            message="Dev mode: Space duplication not available in dev mode. Please use production authentication.",
            space_url=None,
            space_id=None
        )
    
    # Production mode with real OAuth token
    try:
        from backend_deploy import duplicate_space_to_user
        
        user_token = auth.token if auth.token else os.getenv("HF_TOKEN")
        
        if not user_token:
            raise HTTPException(status_code=401, detail="No HuggingFace token available. Please sign in first.")
        
        print(f"[Duplicate] Duplicating space with token (first 10 chars): {user_token[:10]}...")
        
        # Duplicate the space
        success, message, space_url = duplicate_space_to_user(
            from_space_id=request.from_space_id,
            to_space_name=request.to_space_name,
            token=user_token,
            private=request.private
        )
        
        print(f"[Duplicate] Result:")
        print(f"[Duplicate] - Success: {success}")
        print(f"[Duplicate] - Message: {message}")
        print(f"[Duplicate] - Space URL: {space_url}")
        
        if success:
            # Extract space_id from URL
            space_id = space_url.split("/spaces/")[-1] if space_url else None
            
            return DuplicateSpaceResponse(
                success=True,
                message=message,
                space_url=space_url,
                space_id=space_id
            )
        else:
            # Provide user-friendly error messages
            if "401" in message or "Unauthorized" in message:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication failed. Please sign in again with HuggingFace."
                )
            elif "403" in message or "Forbidden" in message or "Permission" in message:
                raise HTTPException(
                    status_code=403,
                    detail="Permission denied. You may not have access to this space."
                )
            elif "404" in message or "not found" in message.lower():
                raise HTTPException(
                    status_code=404,
                    detail="Space not found. Please check the URL and try again."
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=message
                )
                
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"[Duplicate] Error: {error_details}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to duplicate space: {str(e)}"
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
        
        # Check if user owns this repo (for HuggingFace Spaces)
        owned_by_user = False
        repo_id = None
        
        if request.username and result['status'] == 'success':
            # Extract repo_id from URL
            url = result.get('url', '')
            if 'huggingface.co/spaces/' in url:
                # Extract username/repo from URL
                match = re.search(r'huggingface\.co/spaces/([^/]+/[^/?#]+)', url)
                if match:
                    repo_id = match.group(1)
                    # Check if user owns this space
                    if repo_id.startswith(f"{request.username}/"):
                        owned_by_user = True
                        print(f"[Import] User {request.username} owns the imported space: {repo_id}")
        
        # Add ownership info to response
        result['owned_by_user'] = owned_by_user
        result['repo_id'] = repo_id
        
        return ImportResponse(**result)
    
    except Exception as e:
        return ImportResponse(
            status="error",
            message=f"Import failed: {str(e)}",
            code="",
            language="unknown",
            url=request.url,
            metadata={},
            owned_by_user=False,
            repo_id=None
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
            model_id = data.get("model_id", "claude-opus-4.5")
            
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

