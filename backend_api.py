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
from datetime import datetime
import secrets
import base64
import urllib.parse

# Import only what we need, avoiding Gradio UI imports
import sys
import os
from huggingface_hub import InferenceClient
import httpx

# Import system prompts from standalone backend_prompts.py
# No dependencies on Gradio or heavy libraries
print("[Startup] Loading system prompts from backend_prompts...")

try:
    from backend_prompts import (
        HTML_SYSTEM_PROMPT,
        TRANSFORMERS_JS_SYSTEM_PROMPT,
        STREAMLIT_SYSTEM_PROMPT,
        REACT_SYSTEM_PROMPT,
        GRADIO_SYSTEM_PROMPT,
        JSON_SYSTEM_PROMPT,
        GENERIC_SYSTEM_PROMPT
    )
    print("[Startup] ✅ All system prompts loaded successfully from backend_prompts.py")
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

# Define models and languages here to avoid importing Gradio UI
AVAILABLE_MODELS = [
    {"name": "Gemini 3 Pro Preview", "id": "gemini-3-pro-preview", "description": "Google Gemini 3 Pro Preview with deep thinking, Google Search integration, and advanced reasoning"},
    {"name": "Sherlock Dash Alpha", "id": "openrouter/sherlock-dash-alpha", "description": "Sherlock Dash Alpha model via OpenRouter"},
    {"name": "MiniMax M2", "id": "MiniMaxAI/MiniMax-M2", "description": "MiniMax M2 model via HuggingFace InferenceClient with Novita provider"},
    {"name": "DeepSeek V3.2-Exp", "id": "deepseek-ai/DeepSeek-V3.2-Exp", "description": "DeepSeek V3.2 Experimental via HuggingFace"},
    {"name": "DeepSeek R1", "id": "deepseek-ai/DeepSeek-R1-0528", "description": "DeepSeek R1 model for code generation"},
    {"name": "GPT-5", "id": "gpt-5", "description": "OpenAI GPT-5 via OpenRouter"},
    {"name": "Gemini Flash Latest", "id": "gemini-flash-latest", "description": "Google Gemini Flash via OpenRouter"},
    {"name": "Qwen3 Max Preview", "id": "qwen3-max-preview", "description": "Qwen3 Max Preview via DashScope API"},
]

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


# Pydantic models for request/response
class CodeGenerationRequest(BaseModel):
    query: str
    language: str = "html"
    model_id: str = "gemini-3-pro-preview"
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
            
            # Create session
            session_token = secrets.token_urlsafe(32)
            user_sessions[session_token] = {
                "access_token": access_token,
                "user_info": user_info,
                "timestamp": datetime.now(),
                "username": user_info.get("name") or user_info.get("preferred_username") or "user",
                "deployed_spaces": []  # Track deployed spaces for follow-up updates
            }
            
            # Redirect to frontend with session token
            frontend_url = f"{protocol}://{SPACE_HOST}/?session={session_token}"
            return RedirectResponse(url=frontend_url)
            
        except httpx.HTTPError as e:
            print(f"OAuth error: {e}")
            raise HTTPException(status_code=500, detail=f"OAuth failed: {str(e)}")


@app.get("/api/auth/session")
async def get_session(session: str):
    """Get user info from session token"""
    if session not in user_sessions:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    session_data = user_sessions[session]
    return {
        "access_token": session_data["access_token"],
        "user_info": session_data["user_info"],
    }


@app.get("/api/auth/status")
async def auth_status(authorization: Optional[str] = Header(None)):
    """Check authentication status"""
    auth = get_auth_from_header(authorization)
    if auth.is_authenticated():
        return AuthStatus(
            authenticated=True,
            username=auth.username,
            message=f"Authenticated as {auth.username}"
        )
    return AuthStatus(
        authenticated=False,
        username=None,
        message="Not authenticated"
    )


@app.get("/api/generate")
async def generate_code(
    query: str,
    language: str = "html",
    model_id: str = "openrouter/sherlock-dash-alpha",
    provider: str = "auto",
    authorization: Optional[str] = Header(None)
):
    """Generate code based on user query - returns streaming response"""
    # Dev mode: No authentication required - just use server's HF_TOKEN
    # In production, you would check real OAuth tokens here
    
    async def event_stream() -> AsyncGenerator[str, None]:
        """Stream generated code chunks"""
        try:
            # Find the selected model
            selected_model = None
            for model in AVAILABLE_MODELS:
                if model["id"] == model_id:
                    selected_model = model
                    break
            
            if not selected_model:
                selected_model = AVAILABLE_MODELS[0]
            
            # Track generated code
            generated_code = ""
            
            # Select appropriate system prompt based on language
            prompt_map = {
                "html": HTML_SYSTEM_PROMPT,
                "gradio": GRADIO_SYSTEM_PROMPT,
                "streamlit": STREAMLIT_SYSTEM_PROMPT,
                "transformers.js": TRANSFORMERS_JS_SYSTEM_PROMPT,
                "react": REACT_SYSTEM_PROMPT,
                "comfyui": JSON_SYSTEM_PROMPT,
            }
            system_prompt = prompt_map.get(language, GENERIC_SYSTEM_PROMPT.format(language=language))
            
            print(f"[Generate] Using {language} prompt for query: {query[:100]}...")
            
            # Get the real model ID
            actual_model_id = selected_model["id"]
            
            # Determine which provider/API to use based on model ID
            if actual_model_id.startswith("openrouter/"):
                # OpenRouter models - use OpenAI client directly
                from openai import OpenAI
                api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("HF_TOKEN")
                client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=api_key,
                    default_headers={
                        "HTTP-Referer": "https://huggingface.co/spaces/akhaliq/anycoder",
                        "X-Title": "AnyCoder"
                    }
                )
                print(f"[Generate] Using OpenRouter with model: {actual_model_id}")
            elif actual_model_id == "MiniMaxAI/MiniMax-M2":
                # MiniMax M2 via HuggingFace with Novita provider
                hf_token = os.getenv("HF_TOKEN")
                if not hf_token:
                    error_data = json.dumps({
                        "type": "error",
                        "message": "HF_TOKEN environment variable not set. Please set it in your terminal.",
                        "timestamp": datetime.now().isoformat()
                    })
                    yield f"data: {error_data}\n\n"
                    return
                
                # Use OpenAI client with HuggingFace router
                from openai import OpenAI
                client = OpenAI(
                    base_url="https://router.huggingface.co/v1",
                    api_key=hf_token,
                    default_headers={
                        "X-HF-Bill-To": "huggingface"
                    }
                )
                # Add :novita suffix for the API call
                actual_model_id = "MiniMaxAI/MiniMax-M2:novita"
                print(f"[Generate] Using HuggingFace router for MiniMax M2")
            elif actual_model_id.startswith("deepseek-ai/"):
                # DeepSeek models via HuggingFace - use OpenAI client for better streaming
                from openai import OpenAI
                client = OpenAI(
                    base_url="https://api-inference.huggingface.co/v1",
                    api_key=os.getenv("HF_TOKEN")
                )
                print(f"[Generate] Using HuggingFace Inference API for DeepSeek")
            elif actual_model_id == "qwen3-max-preview":
                # Qwen via DashScope (would need separate implementation)
                # For now, fall back to HF
                client = InferenceClient(token=os.getenv("HF_TOKEN"))
            else:
                # Default: HuggingFace models
                client = InferenceClient(token=os.getenv("HF_TOKEN"))
            
            # Prepare messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Generate a {language} application: {query}"}
            ]
            
            # Stream the response
            try:
                stream = client.chat.completions.create(
                    model=actual_model_id,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=10000,
                    stream=True
                )
                
                chunk_count = 0
                print(f"[Generate] Starting to stream from {actual_model_id}...")
                
                for chunk in stream:
                    # Check if choices array has elements before accessing
                    if (hasattr(chunk, 'choices') and 
                        chunk.choices and 
                        len(chunk.choices) > 0 and
                        hasattr(chunk.choices[0], 'delta') and 
                        hasattr(chunk.choices[0].delta, 'content') and 
                        chunk.choices[0].delta.content):
                        content = chunk.choices[0].delta.content
                        generated_code += content
                        chunk_count += 1
                        
                        # Log every 10th chunk to avoid spam
                        if chunk_count % 10 == 0:
                            print(f"[Generate] Streamed {chunk_count} chunks, {len(generated_code)} chars total")
                        
                        # Send chunk as Server-Sent Event - yield immediately for instant streaming
                        event_data = json.dumps({
                            "type": "chunk",
                            "content": content,
                            "timestamp": datetime.now().isoformat()
                        })
                        yield f"data: {event_data}\n\n"
                        
                        # Yield control to allow async processing - no artificial delay
                        await asyncio.sleep(0)
                
                print(f"[Generate] Completed with {chunk_count} chunks, total length: {len(generated_code)}")
                
                # Send completion event
                completion_data = json.dumps({
                    "type": "complete",
                    "code": generated_code,
                    "timestamp": datetime.now().isoformat()
                })
                yield f"data: {completion_data}\n\n"
                
            except Exception as e:
                error_data = json.dumps({
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                yield f"data: {error_data}\n\n"
                
        except Exception as e:
            error_data = json.dumps({
                "type": "error",
                "message": f"Generation error: {str(e)}",
                "timestamp": datetime.now().isoformat()
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
            # Track deployed space in session for follow-up updates
            if session_token and session_token in user_sessions:
                repo_id = space_url.split("/spaces/")[-1] if space_url else None
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
                "repo_id": repo_id if 'repo_id' in locals() else None
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
            model_id = data.get("model_id", "openrouter/sherlock-dash-alpha")
            
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

