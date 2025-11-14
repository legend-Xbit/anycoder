"""
Configuration constants for AnyCoder application.
"""
import os
from datetime import datetime
from typing import Optional

# Gradio supported languages for syntax highlighting
GRADIO_SUPPORTED_LANGUAGES = [
    "python", "json", "html", "javascript"
]

# Search/Replace Constants
SEARCH_START = "<<<<<<< SEARCH"
DIVIDER = "======="
REPLACE_END = ">>>>>>> REPLACE"

# Gradio Documentation Auto-Update System
GRADIO_LLMS_TXT_URL = "https://www.gradio.app/llms.txt"
GRADIO_DOCS_CACHE_FILE = ".gradio_docs_cache.txt"
GRADIO_DOCS_LAST_UPDATE_FILE = ".gradio_docs_last_update.txt"
GRADIO_DOCS_UPDATE_ON_APP_UPDATE = True  # Only update when app is updated, not on a timer

# Global variable to store the current Gradio documentation
_gradio_docs_content: Optional[str] = None
_gradio_docs_last_fetched: Optional[datetime] = None

# ComfyUI Documentation Auto-Update System
COMFYUI_LLMS_TXT_URL = "https://docs.comfy.org/llms.txt"
COMFYUI_DOCS_CACHE_FILE = ".comfyui_docs_cache.txt"
COMFYUI_DOCS_LAST_UPDATE_FILE = ".comfyui_docs_last_update.txt"
COMFYUI_DOCS_UPDATE_ON_APP_UPDATE = True  # Only update when app is updated, not on a timer

# Global variable to store the current ComfyUI documentation
_comfyui_docs_content: Optional[str] = None
_comfyui_docs_last_fetched: Optional[datetime] = None

# FastRTC Documentation Auto-Update System
FASTRTC_LLMS_TXT_URL = "https://fastrtc.org/llms.txt"
FASTRTC_DOCS_CACHE_FILE = ".fastrtc_docs_cache.txt"
FASTRTC_DOCS_LAST_UPDATE_FILE = ".fastrtc_docs_last_update.txt"
FASTRTC_DOCS_UPDATE_ON_APP_UPDATE = True  # Only update when app is updated, not on a timer

# Global variable to store the current FastRTC documentation
_fastrtc_docs_content: Optional[str] = None
_fastrtc_docs_last_fetched: Optional[datetime] = None

# Available Models Configuration
AVAILABLE_MODELS = [
    {
        "name": "DeepSeek V3.2-Exp",
        "id": "deepseek-ai/DeepSeek-V3.2-Exp",
        "description": "DeepSeek V3.2 Experimental model for cutting-edge code generation and reasoning"
    },
    {
        "name": "DeepSeek R1", 
        "id": "deepseek-ai/DeepSeek-R1-0528",
        "description": "DeepSeek R1 model for code generation"
    },
    {
        "name": "GLM-4.6",
        "id": "zai-org/GLM-4.6",
        "description": "GLM-4.6 model for advanced code generation and general tasks"
    },
    {
        "name": "Gemini Flash Latest",
        "id": "gemini-flash-latest",
        "description": "Google Gemini Flash Latest model via native Gemini API"
    },
    {
        "name": "Gemini Flash Lite Latest",
        "id": "gemini-flash-lite-latest",
        "description": "Google Gemini Flash Lite Latest model via OpenAI-compatible API"
    },
    {
        "name": "GPT-5",
        "id": "gpt-5",
        "description": "OpenAI GPT-5 model for advanced code generation and general tasks"
    },
    {
        "name": "GPT-5.1",
        "id": "gpt-5.1",
        "description": "OpenAI GPT-5.1 model via Poe for advanced code generation and general tasks"
    },
    {
        "name": "GPT-5.1 Instant",
        "id": "gpt-5.1-instant",
        "description": "OpenAI GPT-5.1 Instant model via Poe for fast responses"
    },
    {
        "name": "GPT-5.1 Codex",
        "id": "gpt-5.1-codex",
        "description": "OpenAI GPT-5.1 Codex model via Poe optimized for code generation"
    },
    {
        "name": "GPT-5.1 Codex Mini",
        "id": "gpt-5.1-codex-mini",
        "description": "OpenAI GPT-5.1 Codex Mini model via Poe for lightweight code generation"
    },
    {
        "name": "Grok-4",
        "id": "grok-4",
        "description": "Grok-4 model via Poe (OpenAI-compatible) for advanced tasks"
    },
    {
        "name": "Grok-Code-Fast-1",
        "id": "Grok-Code-Fast-1",
        "description": "Grok-Code-Fast-1 model via Poe (OpenAI-compatible) for fast code generation"
    },
    {
        "name": "Claude-Opus-4.1",
        "id": "claude-opus-4.1",
        "description": "Anthropic Claude Opus 4.1 via Poe (OpenAI-compatible)"
    },
    {
        "name": "Claude-Sonnet-4.5",
        "id": "claude-sonnet-4.5",
        "description": "Anthropic Claude Sonnet 4.5 via Poe (OpenAI-compatible)"
    },
    {
        "name": "Claude-Haiku-4.5",
        "id": "claude-haiku-4.5",
        "description": "Anthropic Claude Haiku 4.5 via Poe (OpenAI-compatible)"
    },
    {
        "name": "Qwen3 Max Preview",
        "id": "qwen3-max-preview",
        "description": "Qwen3 Max Preview model via DashScope International API"
    },
    {
        "name": "MiniMax M2",
        "id": "MiniMaxAI/MiniMax-M2",
        "description": "MiniMax M2 model via HuggingFace InferenceClient with Novita provider"
    },
    {
        "name": "Kimi K2 Thinking",
        "id": "moonshotai/Kimi-K2-Thinking",
        "description": "Moonshot Kimi K2 Thinking model for advanced reasoning and code generation"
    }
]

k2_model_name_tag = "moonshotai/Kimi-K2-Thinking"

# Default model selection
DEFAULT_MODEL_NAME = "GPT-5.1 Codex"
DEFAULT_MODEL = None
for _m in AVAILABLE_MODELS:
    if _m.get("name") == DEFAULT_MODEL_NAME:
        DEFAULT_MODEL = _m
        break
if DEFAULT_MODEL is None and AVAILABLE_MODELS:
    DEFAULT_MODEL = AVAILABLE_MODELS[0]

# HF Inference Client
HF_TOKEN = os.getenv('HF_TOKEN')
# Note: HF_TOKEN is checked at runtime when needed, not at import time

# Language choices for code generation
LANGUAGE_CHOICES = [
    "html", "gradio", "transformers.js", "streamlit", "comfyui", "react"
]


def get_gradio_language(language):
    """Map composite options to a supported syntax highlighting."""
    if language == "streamlit":
        return "python"
    if language == "gradio":
        return "python"
    if language == "comfyui":
        return "json"
    if language == "react":
        return "javascript"
    return language if language in GRADIO_SUPPORTED_LANGUAGES else None

