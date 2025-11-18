"""
Standalone model inference and client management for AnyCoder Backend API.
No Gradio dependencies - works with FastAPI/backend only.
"""
import os
from typing import Optional

from openai import OpenAI
from mistralai import Mistral

# Import genai for Gemini 3
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("WARNING: google-genai not available, Gemini 3 will not work")

def get_inference_client(model_id: str, provider: str = "auto"):
    """
    Return an appropriate client based on model_id.
    
    For Gemini 3: Returns genai.Client (native Google SDK)
    For others: Returns OpenAI-compatible client or raises error
    """
    if model_id == "gemini-3-pro-preview":
        if not GEMINI_AVAILABLE:
            raise ImportError("google-genai package required for Gemini 3. Install with: pip install google-genai")
        # Use native Google GenAI client for Gemini 3 Pro Preview with v1alpha API
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable required for Gemini 3")
        return genai.Client(
            api_key=api_key,
            http_options={'api_version': 'v1alpha'}
        )
    
    elif model_id == "qwen3-30b-a3b-instruct-2507":
        # Use DashScope OpenAI client
        return OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    
    elif model_id == "qwen3-30b-a3b-thinking-2507":
        # Use DashScope OpenAI client for Thinking model
        return OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    
    elif model_id == "qwen3-coder-30b-a3b-instruct":
        # Use DashScope OpenAI client for Coder model
        return OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    
    elif model_id == "gpt-5":
        # Use Poe (OpenAI-compatible) client for GPT-5 model
        return OpenAI(
            api_key=os.getenv("POE_API_KEY"),
            base_url="https://api.poe.com/v1"
        )
    
    elif model_id == "gpt-5.1":
        # Use Poe (OpenAI-compatible) client for GPT-5.1 model
        return OpenAI(
            api_key=os.getenv("POE_API_KEY"),
            base_url="https://api.poe.com/v1"
        )
    
    elif model_id == "gpt-5.1-instant":
        # Use Poe (OpenAI-compatible) client for GPT-5.1 Instant model
        return OpenAI(
            api_key=os.getenv("POE_API_KEY"),
            base_url="https://api.poe.com/v1"
        )
    
    elif model_id == "gpt-5.1-codex":
        # Use Poe (OpenAI-compatible) client for GPT-5.1 Codex model
        return OpenAI(
            api_key=os.getenv("POE_API_KEY"),
            base_url="https://api.poe.com/v1"
        )
    
    elif model_id == "gpt-5.1-codex-mini":
        # Use Poe (OpenAI-compatible) client for GPT-5.1 Codex Mini model
        return OpenAI(
            api_key=os.getenv("POE_API_KEY"),
            base_url="https://api.poe.com/v1"
        )
    
    elif model_id == "grok-4":
        # Use Poe (OpenAI-compatible) client for Grok-4 model
        return OpenAI(
            api_key=os.getenv("POE_API_KEY"),
            base_url="https://api.poe.com/v1"
        )
    
    elif model_id == "Grok-Code-Fast-1":
        # Use Poe (OpenAI-compatible) client for Grok-Code-Fast-1 model
        return OpenAI(
            api_key=os.getenv("POE_API_KEY"),
            base_url="https://api.poe.com/v1"
        )
    
    elif model_id == "claude-opus-4.1":
        # Use Poe (OpenAI-compatible) client for Claude-Opus-4.1
        return OpenAI(
            api_key=os.getenv("POE_API_KEY"),
            base_url="https://api.poe.com/v1"
        )
    
    elif model_id == "claude-sonnet-4.5":
        # Use Poe (OpenAI-compatible) client for Claude-Sonnet-4.5
        return OpenAI(
            api_key=os.getenv("POE_API_KEY"),
            base_url="https://api.poe.com/v1"
        )
    
    elif model_id == "claude-haiku-4.5":
        # Use Poe (OpenAI-compatible) client for Claude-Haiku-4.5
        return OpenAI(
            api_key=os.getenv("POE_API_KEY"),
            base_url="https://api.poe.com/v1"
        )
    
    elif model_id == "qwen3-max-preview":
        # Use DashScope International OpenAI client for Qwen3 Max Preview
        return OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    
    elif model_id.startswith("openrouter/"):
        # OpenRouter models
        return OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
        )
    
    elif model_id == "MiniMaxAI/MiniMax-M2":
        # Use HuggingFace Router with Novita provider for MiniMax M2 model
        return OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=os.getenv("HF_TOKEN"),
            default_headers={"X-HF-Bill-To": "huggingface"}
        )
    
    elif model_id == "step-3":
        # Use StepFun API client for Step-3 model
        return OpenAI(
            api_key=os.getenv("STEP_API_KEY"),
            base_url="https://api.stepfun.com/v1"
        )
    
    elif model_id == "codestral-2508" or model_id == "mistral-medium-2508":
        # Use Mistral client for Mistral models
        return Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
    
    elif model_id == "gemini-2.5-flash":
        # Use Google Gemini (OpenAI-compatible) client
        return OpenAI(
            api_key=os.getenv("GEMINI_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
    
    elif model_id == "gemini-2.5-pro":
        # Use Google Gemini Pro (OpenAI-compatible) client
        return OpenAI(
            api_key=os.getenv("GEMINI_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
    
    elif model_id == "gemini-flash-latest":
        # Use Google Gemini Flash Latest (OpenAI-compatible) client
        return OpenAI(
            api_key=os.getenv("GEMINI_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
    
    elif model_id == "gemini-flash-lite-latest":
        # Use Google Gemini Flash Lite Latest (OpenAI-compatible) client
        return OpenAI(
            api_key=os.getenv("GEMINI_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
    
    elif model_id == "kimi-k2-turbo-preview":
        # Use Moonshot AI (OpenAI-compatible) client for Kimi K2 Turbo (Preview)
        return OpenAI(
            api_key=os.getenv("MOONSHOT_API_KEY"),
            base_url="https://api.moonshot.ai/v1",
        )
    
    elif model_id == "moonshotai/Kimi-K2-Thinking":
        # Use HuggingFace Router with Novita provider
        return OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=os.getenv("HF_TOKEN"),
            default_headers={"X-HF-Bill-To": "huggingface"}
        )
    
    elif model_id == "moonshotai/Kimi-K2-Instruct":
        # Use HuggingFace Router with Groq provider
        return OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=os.getenv("HF_TOKEN"),
            default_headers={"X-HF-Bill-To": "huggingface"}
        )
    
    elif model_id.startswith("deepseek-ai/"):
        # DeepSeek models via HuggingFace Router with Novita provider
        return OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=os.getenv("HF_TOKEN"),
            default_headers={"X-HF-Bill-To": "huggingface"}
        )
    
    elif model_id.startswith("zai-org/GLM-4"):
        # GLM models via HuggingFace Router
        return OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=os.getenv("HF_TOKEN"),
            default_headers={"X-HF-Bill-To": "huggingface"}
        )
    
    elif model_id == "stealth-model-1":
        # Use stealth model with generic configuration
        api_key = os.getenv("STEALTH_MODEL_1_API_KEY")
        if not api_key:
            raise ValueError("STEALTH_MODEL_1_API_KEY environment variable is required")
        
        base_url = os.getenv("STEALTH_MODEL_1_BASE_URL")
        if not base_url:
            raise ValueError("STEALTH_MODEL_1_BASE_URL environment variable is required")
        
        return OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
    
    else:
        # Unknown model - try HuggingFace Inference API
        return OpenAI(
            base_url="https://api-inference.huggingface.co/v1",
            api_key=os.getenv("HF_TOKEN")
        )


def get_real_model_id(model_id: str) -> str:
    """Get the real model ID with provider suffixes if needed"""
    if model_id == "stealth-model-1":
        # Get the real model ID from environment variable
        real_model_id = os.getenv("STEALTH_MODEL_1_ID")
        if not real_model_id:
            raise ValueError("STEALTH_MODEL_1_ID environment variable is required")
        return real_model_id
    
    elif model_id == "zai-org/GLM-4.6":
        # GLM-4.6 requires provider suffix in model string for API calls
        return "zai-org/GLM-4.6:zai-org"
    
    elif model_id == "MiniMaxAI/MiniMax-M2":
        # MiniMax M2 needs Novita provider suffix
        return "MiniMaxAI/MiniMax-M2:novita"
    
    elif model_id == "moonshotai/Kimi-K2-Thinking":
        # Kimi K2 Thinking needs Novita provider
        return "moonshotai/Kimi-K2-Thinking:novita"
    
    elif model_id == "moonshotai/Kimi-K2-Instruct":
        # Kimi K2 Instruct needs Groq provider
        return "moonshotai/Kimi-K2-Instruct:groq"
    
    elif model_id.startswith("deepseek-ai/DeepSeek-V3"):
        # DeepSeek V3 models need Novita provider
        return f"{model_id}:novita"
    
    elif model_id == "zai-org/GLM-4.5":
        # GLM-4.5 needs fireworks-ai provider
        return "zai-org/GLM-4.5:fireworks-ai"
    
    return model_id


def create_gemini3_messages(messages: list) -> tuple:
    """
    Convert OpenAI-style messages to Gemini 3 format.
    Returns (contents, tools, config)
    """
    if not GEMINI_AVAILABLE:
        raise ImportError("google-genai package required for Gemini 3")
    
    contents = []
    system_prompt = None
    
    for msg in messages:
        if msg['role'] == 'system':
            system_prompt = msg['content']
        elif msg['role'] in ['user', 'assistant']:
            contents.append(
                types.Content(
                    role="user" if msg['role'] == 'user' else "model",
                    parts=[types.Part.from_text(text=msg['content'])]
                )
            )
    
    # Add system prompt as first user message if exists
    if system_prompt:
        contents.insert(0, types.Content(
            role="user",
            parts=[types.Part.from_text(text=f"System instructions: {system_prompt}")]
        ))
    
    # Configure tools and thinking
    tools = [types.Tool(googleSearch=types.GoogleSearch())]
    config = types.GenerateContentConfig(
        thinkingConfig=types.ThinkingConfig(thinkingLevel="HIGH"),
        tools=tools,
        max_output_tokens=16384
    )
    
    return contents, config


def is_native_sdk_model(model_id: str) -> bool:
    """Check if model uses native SDK (not OpenAI-compatible)"""
    return model_id in ["gemini-3-pro-preview"]


def is_mistral_model(model_id: str) -> bool:
    """Check if model uses Mistral SDK"""
    return model_id in ["codestral-2508", "mistral-medium-2508"]

