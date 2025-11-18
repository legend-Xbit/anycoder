"""
Model inference and client management for AnyCoder.
Handles different model providers and inference clients.
"""
import os
from typing import Dict, List, Optional, Tuple
import re
from http import HTTPStatus

from huggingface_hub import InferenceClient
from openai import OpenAI
from mistralai import Mistral
import dashscope
from google import genai
from google.genai import types

from .config import HF_TOKEN, AVAILABLE_MODELS

# Type definitions
History = List[Dict[str, str]]
Messages = List[Dict[str, str]]

def get_inference_client(model_id, provider="auto"):
    """Return an InferenceClient with provider based on model_id and user selection."""
    if model_id == "gemini-3.0-pro":
        # Use Poe (OpenAI-compatible) client for Gemini 3.0 Pro
        return OpenAI(
            api_key=os.getenv("POE_API_KEY"),
            base_url="https://api.poe.com/v1"
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
    elif model_id == "openrouter/sonoma-dusk-alpha":
        # Use OpenRouter client for Sonoma Dusk Alpha model
        return OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
        )
    elif model_id == "openrouter/sonoma-sky-alpha":
        # Use OpenRouter client for Sonoma Sky Alpha model
        return OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
        )
    elif model_id == "openrouter/sherlock-dash-alpha":
        # Use OpenRouter client for Sherlock Dash Alpha model
        return OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
        )
    elif model_id == "openrouter/sherlock-think-alpha":
        # Use OpenRouter client for Sherlock Think Alpha model
        return OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
        )
    elif model_id == "MiniMaxAI/MiniMax-M2":
        # Use HuggingFace InferenceClient with Novita provider for MiniMax M2 model
        provider = "novita"
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
        # Use HuggingFace InferenceClient with Novita provider for Kimi K2 Thinking
        provider = "novita"
    elif model_id == "stealth-model-1":
        # Use stealth model with generic configuration
        api_key = os.getenv("STEALTH_MODEL_1_API_KEY")
        if not api_key:
            raise ValueError("STEALTH_MODEL_1_API_KEY environment variable is required for Carrot model")
        
        base_url = os.getenv("STEALTH_MODEL_1_BASE_URL")
        if not base_url:
            raise ValueError("STEALTH_MODEL_1_BASE_URL environment variable is required for Carrot model")
        
        return OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
    elif model_id == "moonshotai/Kimi-K2-Instruct":
        provider = "groq"
    elif model_id == "deepseek-ai/DeepSeek-V3.1":
        provider = "novita"
    elif model_id == "deepseek-ai/DeepSeek-V3.1-Terminus":
        provider = "novita"
    elif model_id == "deepseek-ai/DeepSeek-V3.2-Exp":
        provider = "novita"
    elif model_id == "zai-org/GLM-4.5":
        provider = "fireworks-ai"
    elif model_id == "zai-org/GLM-4.6":
        # Use auto provider for GLM-4.6, HuggingFace will select best available
        provider = "auto"
    return InferenceClient(
        provider=provider,
        api_key=HF_TOKEN,
        bill_to="huggingface"
    )

# Helper function to get real model ID for stealth models and special cases
def get_real_model_id(model_id: str) -> str:
    """Get the real model ID, checking environment variables for stealth models and handling special model formats"""
    if model_id == "stealth-model-1":
        # Get the real model ID from environment variable
        real_model_id = os.getenv("STEALTH_MODEL_1_ID")
        if not real_model_id:
            raise ValueError("STEALTH_MODEL_1_ID environment variable is required for Carrot model")
        
        return real_model_id
    elif model_id == "zai-org/GLM-4.6":
        # GLM-4.6 requires provider suffix in model string for API calls
        return "zai-org/GLM-4.6:zai-org"
    return model_id

# Type definitions
History = List[Tuple[str, str]]
Messages = List[Dict[str, str]]

def history_to_messages(history: History, system: str) -> Messages:
    messages = [{'role': 'system', 'content': system}]
    for h in history:
        # Handle multimodal content in history
        user_content = h[0]
        if isinstance(user_content, list):
            # Extract text from multimodal content
            text_content = ""
            for item in user_content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_content += item.get("text", "")
            user_content = text_content if text_content else str(user_content)
        
        messages.append({'role': 'user', 'content': user_content})
        messages.append({'role': 'assistant', 'content': h[1]})
    return messages

def history_to_chatbot_messages(history: History) -> List[Dict[str, str]]:
    """Convert history tuples to chatbot message format"""
    messages = []
    for user_msg, assistant_msg in history:
        # Handle multimodal content
        if isinstance(user_msg, list):
            text_content = ""
            for item in user_msg:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_content += item.get("text", "")
            user_msg = text_content if text_content else str(user_msg)
        
        messages.append({"role": "user", "content": user_msg})
        messages.append({"role": "assistant", "content": assistant_msg})
    return messages

def strip_tool_call_markers(text):
    """Remove TOOL_CALL markers that some LLMs (like Qwen) add to their output."""
    if not text:
        return text
    # Remove [TOOL_CALL] and [/TOOL_CALL] markers
    text = re.sub(r'\[/?TOOL_CALL\]', '', text, flags=re.IGNORECASE)
    # Remove standalone }} that appears with tool calls
    # Only remove if it's on its own line or at the end
    text = re.sub(r'^\s*\}\}\s*$', '', text, flags=re.MULTILINE)
    return text.strip()

def remove_code_block(text):
    # First strip any tool call markers
    text = strip_tool_call_markers(text)
    
    # Try to match code blocks with language markers
    patterns = [
        r'```(?:html|HTML)\n([\s\S]+?)\n```',  # Match ```html or ```HTML
        r'```\n([\s\S]+?)\n```',               # Match code blocks without language markers
        r'```([\s\S]+?)```'                      # Match code blocks without line breaks
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            extracted = match.group(1).strip()
            # Remove a leading language marker line (e.g., 'python') if present
            if extracted.split('\n', 1)[0].strip().lower() in ['python', 'html', 'css', 'javascript', 'json', 'c', 'cpp', 'markdown', 'latex', 'jinja2', 'typescript', 'yaml', 'dockerfile', 'shell', 'r', 'sql', 'sql-mssql', 'sql-mysql', 'sql-mariadb', 'sql-sqlite', 'sql-cassandra', 'sql-plSQL', 'sql-hive', 'sql-pgsql', 'sql-gql', 'sql-gpsql', 'sql-sparksql', 'sql-esper']:
                return extracted.split('\n', 1)[1] if '\n' in extracted else ''
            # If HTML markup starts later in the block (e.g., Poe injected preface), trim to first HTML root
            html_root_idx = None
            for tag in ['<!DOCTYPE html', '<html']:
                idx = extracted.find(tag)
                if idx != -1:
                    html_root_idx = idx if html_root_idx is None else min(html_root_idx, idx)
            if html_root_idx is not None and html_root_idx > 0:
                return extracted[html_root_idx:].strip()
            return extracted
    # If no code block is found, check if the entire text is HTML
    stripped = text.strip()
    if stripped.startswith('<!DOCTYPE html>') or stripped.startswith('<html') or stripped.startswith('<'):
        # If HTML root appears later (e.g., Poe preface), trim to first HTML root
        for tag in ['<!DOCTYPE html', '<html']:
            idx = stripped.find(tag)
            if idx > 0:
                return stripped[idx:].strip()
        return stripped
    # Special handling for python: remove python marker
    if text.strip().startswith('```python'):
        return text.strip()[9:-3].strip()
    # Remove a leading language marker line if present (fallback)
    lines = text.strip().split('\n', 1)
    if lines[0].strip().lower() in ['python', 'html', 'css', 'javascript', 'json', 'c', 'cpp', 'markdown', 'latex', 'jinja2', 'typescript', 'yaml', 'dockerfile', 'shell', 'r', 'sql', 'sql-mssql', 'sql-mysql', 'sql-mariadb', 'sql-sqlite', 'sql-cassandra', 'sql-plSQL', 'sql-hive', 'sql-pgsql', 'sql-gql', 'sql-gpsql', 'sql-sparksql', 'sql-esper']:
        return lines[1] if len(lines) > 1 else ''
    return text.strip()

## React CDN compatibility fixer removed per user preference

def strip_thinking_tags(text: str) -> str:
    """Strip <think> tags and [TOOL_CALL] markers from streaming output."""
    if not text:
        return text
    # Remove <think> opening tags
    text = re.sub(r'<think>', '', text, flags=re.IGNORECASE)
    # Remove </think> closing tags
    text = re.sub(r'</think>', '', text, flags=re.IGNORECASE)
    # Remove [TOOL_CALL] markers
    text = re.sub(r'\[/?TOOL_CALL\]', '', text, flags=re.IGNORECASE)
    return text

def strip_placeholder_thinking(text: str) -> str:
    """Remove placeholder 'Thinking...' status lines from streamed text."""
    if not text:
        return text
    # Matches lines like: "Thinking..." or "Thinking... (12s elapsed)"
    return re.sub(r"(?mi)^[\t ]*Thinking\.\.\.(?:\s*\(\d+s elapsed\))?[\t ]*$\n?", "", text)

def is_placeholder_thinking_only(text: str) -> bool:
    """Return True if text contains only 'Thinking...' placeholder lines (with optional elapsed)."""
    if not text:
        return False
    stripped = text.strip()
    if not stripped:
        return False
    return re.fullmatch(r"(?s)(?:\s*Thinking\.\.\.(?:\s*\(\d+s elapsed\))?\s*)+", stripped) is not None

def extract_last_thinking_line(text: str) -> str:
    """Extract the last 'Thinking...' line to display as status."""
    matches = list(re.finditer(r"Thinking\.\.\.(?:\s*\(\d+s elapsed\))?", text))
    return matches[-1].group(0) if matches else "Thinking..."

