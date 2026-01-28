"""
Standalone model inference and client management for AnyCoder Backend API.
No Gradio dependencies - works with FastAPI/backend only.
"""
import os
from typing import Optional

from openai import OpenAI

def get_inference_client(model_id: str, provider: str = "auto"):
    """
    Return an appropriate client based on model_id.
    
    Returns OpenAI-compatible client for all models or raises error if not configured.
    """
    if model_id == "MiniMaxAI/MiniMax-M2" or model_id == "MiniMaxAI/MiniMax-M2.1":
        # Use HuggingFace Router with Novita provider for MiniMax M2 models
        return OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=os.getenv("HF_TOKEN"),
            default_headers={"X-HF-Bill-To": "huggingface"}
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
    
    elif model_id.startswith("moonshotai/Kimi-K2"):
        # Kimi K2 models via HuggingFace Router
        return OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=os.getenv("HF_TOKEN"),
            default_headers={"X-HF-Bill-To": "huggingface"}
        )
    
    else:
        # Unknown model - try HuggingFace Inference API
        return OpenAI(
            base_url="https://api-inference.huggingface.co/v1",
            api_key=os.getenv("HF_TOKEN")
        )


def get_real_model_id(model_id: str) -> str:
    """Get the real model ID with provider suffixes if needed"""
    if model_id == "zai-org/GLM-4.6":
        # GLM-4.6 requires Cerebras provider suffix in model string for API calls
        return "zai-org/GLM-4.6:cerebras"
    
    elif model_id == "MiniMaxAI/MiniMax-M2" or model_id == "MiniMaxAI/MiniMax-M2.1":
        # MiniMax M2 and M2.1 need Novita provider suffix
        return f"{model_id}:novita"
    
    elif model_id == "moonshotai/Kimi-K2-Thinking":
        # Kimi K2 Thinking needs Together AI provider
        return "moonshotai/Kimi-K2-Thinking:together"
    
    elif model_id == "moonshotai/Kimi-K2-Instruct":
        # Kimi K2 Instruct needs Groq provider
        return "moonshotai/Kimi-K2-Instruct:groq"
    
    elif model_id.startswith("deepseek-ai/DeepSeek-V3") or model_id.startswith("deepseek-ai/DeepSeek-R1"):
        # DeepSeek V3 and R1 models need Novita provider
        return f"{model_id}:novita"
    
    elif model_id == "zai-org/GLM-4.5":
        # GLM-4.5 needs fireworks-ai provider
        return "zai-org/GLM-4.5:fireworks-ai"
    
    elif model_id == "zai-org/GLM-4.7":
        # GLM-4.7 needs cerebras provider suffix
        return "zai-org/GLM-4.7:cerebras"
    
    elif model_id == "zai-org/GLM-4.7-Flash":
        # GLM-4.7-Flash via HuggingFace Router with Novita provider
        return "zai-org/GLM-4.7-Flash:novita"
    
    elif model_id == "moonshotai/Kimi-K2.5":
        # Kimi K2.5 needs Novita provider
        return "moonshotai/Kimi-K2.5:novita"
    
    return model_id


def is_native_sdk_model(model_id: str) -> bool:
    """Check if model uses native SDK (not OpenAI-compatible)"""
    return False


def is_mistral_model(model_id: str) -> bool:
    """Check if model uses Mistral SDK"""
    return False

