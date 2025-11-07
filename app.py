import os
import re
from http import HTTPStatus
from typing import Dict, List, Optional, Tuple
import base64
import mimetypes
import numpy as np
from PIL import Image
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import html2text
import json
import time
import webbrowser
import urllib.parse
import copy
import html

import gradio as gr
from huggingface_hub import InferenceClient
from huggingface_hub import HfApi
import tempfile
from openai import OpenAI
import uuid
import datetime
from mistralai import Mistral
import shutil
import urllib.parse
import mimetypes
import threading
import atexit
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import dashscope

# Gradio supported languages for syntax highlighting
GRADIO_SUPPORTED_LANGUAGES = [
    "python", "json", "html", "javascript"
]

def get_gradio_language(language):
    # Map composite options to a supported syntax highlighting
    if language == "streamlit":
        return "python"
    if language == "gradio":
        return "python"
    if language == "comfyui":
        return "json"
    if language == "react":
        return "javascript"
    return language if language in GRADIO_SUPPORTED_LANGUAGES else None

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
_gradio_docs_content: str | None = None
_gradio_docs_last_fetched: Optional[datetime] = None

# ComfyUI Documentation Auto-Update System
COMFYUI_LLMS_TXT_URL = "https://docs.comfy.org/llms.txt"
COMFYUI_DOCS_CACHE_FILE = ".comfyui_docs_cache.txt"
COMFYUI_DOCS_LAST_UPDATE_FILE = ".comfyui_docs_last_update.txt"
COMFYUI_DOCS_UPDATE_ON_APP_UPDATE = True  # Only update when app is updated, not on a timer

# Global variable to store the current ComfyUI documentation
_comfyui_docs_content: str | None = None
_comfyui_docs_last_fetched: Optional[datetime] = None

# FastRTC Documentation Auto-Update System
FASTRTC_LLMS_TXT_URL = "https://fastrtc.org/llms.txt"
FASTRTC_DOCS_CACHE_FILE = ".fastrtc_docs_cache.txt"
FASTRTC_DOCS_LAST_UPDATE_FILE = ".fastrtc_docs_last_update.txt"
FASTRTC_DOCS_UPDATE_ON_APP_UPDATE = True  # Only update when app is updated, not on a timer

# Global variable to store the current FastRTC documentation
_fastrtc_docs_content: str | None = None
_fastrtc_docs_last_fetched: Optional[datetime] = None

def fetch_gradio_docs() -> str | None:
    """Fetch the latest Gradio documentation from llms.txt"""
    try:
        response = requests.get(GRADIO_LLMS_TXT_URL, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Warning: Failed to fetch Gradio docs from {GRADIO_LLMS_TXT_URL}: {e}")
        return None

def fetch_comfyui_docs() -> str | None:
    """Fetch the latest ComfyUI documentation from llms.txt"""
    try:
        response = requests.get(COMFYUI_LLMS_TXT_URL, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Warning: Failed to fetch ComfyUI docs from {COMFYUI_LLMS_TXT_URL}: {e}")
        return None

def fetch_fastrtc_docs() -> str | None:
    """Fetch the latest FastRTC documentation from llms.txt"""
    try:
        response = requests.get(FASTRTC_LLMS_TXT_URL, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Warning: Failed to fetch FastRTC docs from {FASTRTC_LLMS_TXT_URL}: {e}")
        return None

def filter_problematic_instructions(content: str) -> str:
    """Filter out problematic instructions that cause LLM to stop generation prematurely"""
    if not content:
        return content
    
    # List of problematic phrases that cause early termination when LLM encounters ``` in user code
    problematic_patterns = [
        r"Output ONLY the code inside a ``` code block, and do not include any explanations or extra text",
        r"output only the code inside a ```.*?``` code block",
        r"Always output only the.*?code.*?inside.*?```.*?```.*?block",
        r"Return ONLY the code inside a.*?```.*?``` code block",
        r"Do NOT add the language name at the top of the code output",
        r"do not include any explanations or extra text",
        r"Always output only the.*?code blocks.*?shown above, and do not include any explanations",
        r"Output.*?ONLY.*?code.*?inside.*?```.*?```",
        r"Return.*?ONLY.*?code.*?inside.*?```.*?```",
        r"Generate.*?ONLY.*?code.*?inside.*?```.*?```",
        r"Provide.*?ONLY.*?code.*?inside.*?```.*?```",
    ]
    
    # Remove problematic patterns
    filtered_content = content
    for pattern in problematic_patterns:
        # Use case-insensitive matching
        filtered_content = re.sub(pattern, "", filtered_content, flags=re.IGNORECASE | re.DOTALL)
    
    # Clean up any double newlines or extra whitespace left by removals
    filtered_content = re.sub(r'\n\s*\n\s*\n', '\n\n', filtered_content)
    filtered_content = re.sub(r'^\s+', '', filtered_content, flags=re.MULTILINE)
    
    return filtered_content

def load_cached_gradio_docs() -> str | None:
    """Load cached Gradio documentation from file"""
    try:
        if os.path.exists(GRADIO_DOCS_CACHE_FILE):
            with open(GRADIO_DOCS_CACHE_FILE, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        print(f"Warning: Failed to load cached Gradio docs: {e}")
    return None

def save_gradio_docs_cache(content: str):
    """Save Gradio documentation to cache file"""
    try:
        with open(GRADIO_DOCS_CACHE_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        with open(GRADIO_DOCS_LAST_UPDATE_FILE, 'w', encoding='utf-8') as f:
            f.write(datetime.now().isoformat())
    except Exception as e:
        print(f"Warning: Failed to save Gradio docs cache: {e}")

def load_comfyui_docs_cache() -> str | None:
    """Load ComfyUI documentation from cache file"""
    try:
        if os.path.exists(COMFYUI_DOCS_CACHE_FILE):
            with open(COMFYUI_DOCS_CACHE_FILE, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        print(f"Warning: Failed to load cached ComfyUI docs: {e}")
    return None

def save_comfyui_docs_cache(content: str):
    """Save ComfyUI documentation to cache file"""
    try:
        with open(COMFYUI_DOCS_CACHE_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        with open(COMFYUI_DOCS_LAST_UPDATE_FILE, 'w', encoding='utf-8') as f:
            f.write(datetime.now().isoformat())
    except Exception as e:
        print(f"Warning: Failed to save ComfyUI docs cache: {e}")

def load_fastrtc_docs_cache() -> str | None:
    """Load FastRTC documentation from cache file"""
    try:
        if os.path.exists(FASTRTC_DOCS_CACHE_FILE):
            with open(FASTRTC_DOCS_CACHE_FILE, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        print(f"Warning: Failed to load cached FastRTC docs: {e}")
    return None

def save_fastrtc_docs_cache(content: str):
    """Save FastRTC documentation to cache file"""
    try:
        with open(FASTRTC_DOCS_CACHE_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        with open(FASTRTC_DOCS_LAST_UPDATE_FILE, 'w', encoding='utf-8') as f:
            f.write(datetime.now().isoformat())
    except Exception as e:
        print(f"Warning: Failed to save FastRTC docs cache: {e}")

def get_last_update_time() -> Optional[datetime]:
    """Get the last update time from file"""
    try:
        if os.path.exists(GRADIO_DOCS_LAST_UPDATE_FILE):
            with open(GRADIO_DOCS_LAST_UPDATE_FILE, 'r', encoding='utf-8') as f:
                return datetime.fromisoformat(f.read().strip())
    except Exception as e:
        print(f"Warning: Failed to read last update time: {e}")
    return None

def should_update_gradio_docs() -> bool:
    """Check if Gradio documentation should be updated"""
    # Only update if we don't have cached content (first run or cache deleted)
    return not os.path.exists(GRADIO_DOCS_CACHE_FILE)

def should_update_comfyui_docs() -> bool:
    """Check if ComfyUI documentation should be updated"""
    # Only update if we don't have cached content (first run or cache deleted)
    return not os.path.exists(COMFYUI_DOCS_CACHE_FILE)

def should_update_fastrtc_docs() -> bool:
    """Check if FastRTC documentation should be updated"""
    # Only update if we don't have cached content (first run or cache deleted)
    return not os.path.exists(FASTRTC_DOCS_CACHE_FILE)

def force_update_gradio_docs():
    """
    Force an update of Gradio documentation (useful when app is updated).
    
    To manually refresh docs, you can call this function or simply delete the cache file:
    rm .gradio_docs_cache.txt && restart the app
    """
    global _gradio_docs_content, _gradio_docs_last_fetched
    
    print("🔄 Forcing Gradio documentation update...")
    latest_content = fetch_gradio_docs()
    
    if latest_content:
        # Filter out problematic instructions that cause early termination
        filtered_content = filter_problematic_instructions(latest_content)
        _gradio_docs_content = filtered_content
        _gradio_docs_last_fetched = datetime.now()
        save_gradio_docs_cache(filtered_content)
        update_gradio_system_prompts()
        print("✅ Gradio documentation updated successfully")
        return True
    else:
        print("❌ Failed to update Gradio documentation")
        return False

def force_update_comfyui_docs():
    """
    Force an update of ComfyUI documentation (useful when app is updated).
    
    To manually refresh docs, you can call this function or simply delete the cache file:
    rm .comfyui_docs_cache.txt && restart the app
    """
    global _comfyui_docs_content, _comfyui_docs_last_fetched
    
    print("🔄 Forcing ComfyUI documentation update...")
    latest_content = fetch_comfyui_docs()
    
    if latest_content:
        # Filter out problematic instructions that cause early termination
        filtered_content = filter_problematic_instructions(latest_content)
        _comfyui_docs_content = filtered_content
        _comfyui_docs_last_fetched = datetime.now()
        save_comfyui_docs_cache(filtered_content)
        update_json_system_prompts()
        print("✅ ComfyUI documentation updated successfully")
        return True
    else:
        print("❌ Failed to update ComfyUI documentation")
        return False

def force_update_fastrtc_docs():
    """
    Force an update of FastRTC documentation (useful when app is updated).
    
    To manually refresh docs, you can call this function or simply delete the cache file:
    rm .fastrtc_docs_cache.txt && restart the app
    """
    global _fastrtc_docs_content, _fastrtc_docs_last_fetched
    
    print("🔄 Forcing FastRTC documentation update...")
    latest_content = fetch_fastrtc_docs()
    
    if latest_content:
        # Filter out problematic instructions that cause early termination
        filtered_content = filter_problematic_instructions(latest_content)
        _fastrtc_docs_content = filtered_content
        _fastrtc_docs_last_fetched = datetime.now()
        save_fastrtc_docs_cache(filtered_content)
        update_gradio_system_prompts()
        print("✅ FastRTC documentation updated successfully")
        return True
    else:
        print("❌ Failed to update FastRTC documentation")
        return False

def get_gradio_docs_content() -> str:
    """Get the current Gradio documentation content, updating if necessary"""
    global _gradio_docs_content, _gradio_docs_last_fetched
    
    # Check if we need to update
    if (_gradio_docs_content is None or 
        _gradio_docs_last_fetched is None or 
        should_update_gradio_docs()):
        
        print("Updating Gradio documentation...")
        
        # Try to fetch latest content
        latest_content = fetch_gradio_docs()
        
        if latest_content:
            # Filter out problematic instructions that cause early termination
            filtered_content = filter_problematic_instructions(latest_content)
            _gradio_docs_content = filtered_content
            _gradio_docs_last_fetched = datetime.now()
            save_gradio_docs_cache(filtered_content)
            print("✅ Gradio documentation updated successfully")
        else:
            # Fallback to cached content
            cached_content = load_cached_gradio_docs()
            if cached_content:
                _gradio_docs_content = cached_content
                _gradio_docs_last_fetched = datetime.now()
                print("⚠️ Using cached Gradio documentation (network fetch failed)")
            else:
                # Fallback to minimal content
                _gradio_docs_content = """
                # Gradio API Reference (Offline Fallback)
                
                This is a minimal fallback when documentation cannot be fetched.
                Please check your internet connection for the latest API reference.
                
                Basic Gradio components: Button, Textbox, Slider, Image, Audio, Video, File, etc.
                Use gr.Blocks() for custom layouts and gr.Interface() for simple apps.
                """
                print("❌ Using minimal fallback documentation")
    
    return _gradio_docs_content or ""

def get_comfyui_docs_content() -> str:
    """Get the current ComfyUI documentation content, updating if necessary"""
    global _comfyui_docs_content, _comfyui_docs_last_fetched
    
    # Check if we need to update
    if (_comfyui_docs_content is None or 
        _comfyui_docs_last_fetched is None or 
        should_update_comfyui_docs()):
        
        print("Updating ComfyUI documentation...")
        
        # Try to fetch latest content
        latest_content = fetch_comfyui_docs()
        
        if latest_content:
            # Filter out problematic instructions that cause early termination
            filtered_content = filter_problematic_instructions(latest_content)
            _comfyui_docs_content = filtered_content
            _comfyui_docs_last_fetched = datetime.now()
            save_comfyui_docs_cache(filtered_content)
            print("✅ ComfyUI documentation updated successfully")
        else:
            # Fallback to cached content
            cached_content = load_comfyui_docs_cache()
            if cached_content:
                _comfyui_docs_content = cached_content
                _comfyui_docs_last_fetched = datetime.now()
                print("⚠️ Using cached ComfyUI documentation (network fetch failed)")
            else:
                # Fallback to minimal content
                _comfyui_docs_content = """
                # ComfyUI API Reference (Offline Fallback)
                
                This is a minimal fallback when documentation cannot be fetched.
                Please check your internet connection for the latest API reference.
                
                Basic ComfyUI workflow structure: nodes, connections, inputs, outputs.
                Use CheckpointLoaderSimple, CLIPTextEncode, KSampler for basic workflows.
                """
                print("❌ Using minimal fallback documentation")
    
    return _comfyui_docs_content or ""

def get_fastrtc_docs_content() -> str:
    """Get the current FastRTC documentation content, updating if necessary"""
    global _fastrtc_docs_content, _fastrtc_docs_last_fetched
    
    # Check if we need to update
    if (_fastrtc_docs_content is None or 
        _fastrtc_docs_last_fetched is None or 
        should_update_fastrtc_docs()):
        
        print("Updating FastRTC documentation...")
        
        # Try to fetch latest content
        latest_content = fetch_fastrtc_docs()
        
        if latest_content:
            # Filter out problematic instructions that cause early termination
            filtered_content = filter_problematic_instructions(latest_content)
            _fastrtc_docs_content = filtered_content
            _fastrtc_docs_last_fetched = datetime.now()
            save_fastrtc_docs_cache(filtered_content)
            print("✅ FastRTC documentation updated successfully")
        else:
            # Fallback to cached content
            cached_content = load_fastrtc_docs_cache()
            if cached_content:
                _fastrtc_docs_content = cached_content
                _fastrtc_docs_last_fetched = datetime.now()
                print("⚠️ Using cached FastRTC documentation (network fetch failed)")
            else:
                # Fallback to minimal content
                _fastrtc_docs_content = """
                # FastRTC API Reference (Offline Fallback)
                
                This is a minimal fallback when documentation cannot be fetched.
                Please check your internet connection for the latest API reference.
                
                Basic FastRTC usage: Stream class, handlers, real-time audio/video processing.
                Use Stream(handler, modality, mode) for real-time communication apps.
                """
                print("❌ Using minimal fallback documentation")
    
    return _fastrtc_docs_content or ""

def update_gradio_system_prompts():
    """Update the global Gradio system prompts with latest documentation"""
    global GRADIO_SYSTEM_PROMPT, GRADIO_SYSTEM_PROMPT_WITH_SEARCH
    
    docs_content = get_gradio_docs_content()
    fastrtc_content = get_fastrtc_docs_content()
    
    # Base system prompt
    base_prompt = """You are an expert Gradio developer. Create a complete, working Gradio application based on the user's request. Generate all necessary code to make the application functional and runnable.

## Multi-File Application Structure

When creating complex Gradio applications, organize your code into multiple files for better maintainability:

**File Organization:**
- `app.py` - Main application entry point with Gradio interface
- `utils.py` - Utility functions and helpers
- `models.py` - Model loading and inference functions
- `config.py` - Configuration and constants
- `requirements.txt` - Python dependencies
- Additional modules as needed (e.g., `data_processing.py`, `ui_components.py`)

**🚨 CRITICAL: DO NOT Generate README.md Files**
- NEVER generate README.md files under any circumstances
- A template README.md is automatically provided and will be overridden by the deployment system
- Generating a README.md will break the deployment process
- Only generate the code files listed above

**Output Format for Multi-File Apps:**
When generating multi-file applications, use this exact format:

```
=== app.py ===
[main application code]

=== utils.py ===
[utility functions]

=== requirements.txt ===
[dependencies]
```

**🚨 CRITICAL: Always Generate requirements.txt for New Applications**
- ALWAYS include requirements.txt when creating new Gradio applications
- Generate comprehensive, production-ready dependencies based on your code
- Include not just direct imports but also commonly needed companion packages
- Use correct PyPI package names (e.g., PIL → Pillow, sklearn → scikit-learn)
- For diffusers: use `git+https://github.com/huggingface/diffusers`
- For transformers: use `git+https://github.com/huggingface/transformers`
- Include supporting packages (accelerate, torch, tokenizers, etc.) when using ML libraries
- Your requirements.txt should ensure the application works smoothly in production

**🚨 CRITICAL: requirements.txt Formatting Rules**
- Output ONLY plain text package names, one per line
- Do NOT use markdown formatting (no ```, no bold, no headings, no lists with * or -)
- Do NOT add explanatory text or descriptions
- Do NOT wrap in code blocks
- Just raw package names as they would appear in a real requirements.txt file
- Example of CORRECT format:
  gradio
  torch
  transformers
- Example of INCORRECT format (DO NOT DO THIS):
  ```
  gradio  # For web interface
  **Core dependencies:**
  - torch
  ```

**Single vs Multi-File Decision:**
- Use single file for simple applications (< 100 lines) - but still generate requirements.txt if dependencies exist
- Use multi-file structure for complex applications with:
  - Multiple models or processing pipelines
  - Extensive utility functions
  - Complex UI with many components
  - Data processing workflows
  - When user specifically requests modular structure

🚨 IMPORTANT: If the user is asking to use external APIs (like OpenRouter, OpenAI API, Hugging Face Inference API, etc.), DO NOT use @spaces.GPU decorators or any ZeroGPU features. External APIs handle the model inference remotely, so GPU allocation on the Spaces instance is not needed.

🚨 CRITICAL REQUIREMENT: If the user provides ANY diffusion model code (FLUX, Stable Diffusion, etc.) that runs locally (not via API), you MUST implement ZeroGPU ahead-of-time (AoT) compilation. This is mandatory and provides 1.3x-1.8x performance improvements. Do not create basic Gradio apps without AoT optimization for diffusion models.

## ZeroGPU Integration (MANDATORY)

ALWAYS use ZeroGPU for GPU-dependent functions in Gradio apps:

1. Import the spaces module: `import spaces`
2. Decorate GPU-dependent functions with `@spaces.GPU`
3. Specify appropriate duration based on expected runtime:
   - Quick inference (< 30s): `@spaces.GPU(duration=30)`
   - Standard generation (30-60s): `@spaces.GPU` (default 60s)
   - Complex generation (60-120s): `@spaces.GPU(duration=120)`
   - Heavy processing (120-180s): `@spaces.GPU(duration=180)`

Example usage:
```python
import spaces
from diffusers import DiffusionPipeline

pipe = DiffusionPipeline.from_pretrained(...)
pipe.to('cuda')

@spaces.GPU(duration=120)
def generate(prompt):
    return pipe(prompt).images

gr.Interface(
    fn=generate,
    inputs=gr.Text(),
    outputs=gr.Gallery(),
).launch()
```

Duration Guidelines:
- Shorter durations improve queue priority for users
- Text-to-image: typically 30-60 seconds
- Image-to-image: typically 20-40 seconds  
- Video generation: typically 60-180 seconds
- Audio/music generation: typically 30-90 seconds
- Model loading + inference: add 10-30s buffer
- AoT compilation during startup: use @spaces.GPU(duration=1500) for maximum allowed duration

Functions that typically need @spaces.GPU:
- Image generation (text-to-image, image-to-image)
- Video generation
- Audio/music generation
- Model inference with transformers, diffusers
- Any function using .to('cuda') or GPU operations

## CRITICAL: Use ZeroGPU AoT Compilation for ALL Diffusion Models

FOR ANY DIFFUSION MODEL (FLUX, Stable Diffusion, etc.), YOU MUST IMPLEMENT AHEAD-OF-TIME COMPILATION.
This is NOT optional - it provides 1.3x-1.8x speedup and is essential for production ZeroGPU Spaces.

ALWAYS implement this pattern for diffusion models:

### MANDATORY: Basic AoT Compilation Pattern
YOU MUST USE THIS EXACT PATTERN for any diffusion model (FLUX, Stable Diffusion, etc.):

1. ALWAYS add AoT compilation function with @spaces.GPU(duration=1500)
2. ALWAYS use spaces.aoti_capture to capture inputs
3. ALWAYS use torch.export.export to export the transformer
4. ALWAYS use spaces.aoti_compile to compile
5. ALWAYS use spaces.aoti_apply to apply to pipeline

### Required AoT Implementation
```python
import spaces
import torch
from diffusers import DiffusionPipeline

MODEL_ID = 'black-forest-labs/FLUX.1-dev'
pipe = DiffusionPipeline.from_pretrained(MODEL_ID, torch_dtype=torch.bfloat16)
pipe.to('cuda')

@spaces.GPU(duration=1500)  # Maximum duration allowed during startup
def compile_transformer():
    # 1. Capture example inputs
    with spaces.aoti_capture(pipe.transformer) as call:
        pipe("arbitrary example prompt")
    
    # 2. Export the model
    exported = torch.export.export(
        pipe.transformer,
        args=call.args,
        kwargs=call.kwargs,
    )
    
    # 3. Compile the exported model
    return spaces.aoti_compile(exported)

# 4. Apply compiled model to pipeline
compiled_transformer = compile_transformer()
spaces.aoti_apply(compiled_transformer, pipe.transformer)

@spaces.GPU
def generate(prompt):
    return pipe(prompt).images
```

### Advanced Optimizations

#### FP8 Quantization (Additional 1.2x speedup on H200)
```python
from torchao.quantization import quantize_, Float8DynamicActivationFloat8WeightConfig

@spaces.GPU(duration=1500)
def compile_transformer_with_quantization():
    # Quantize before export for FP8 speedup
    quantize_(pipe.transformer, Float8DynamicActivationFloat8WeightConfig())
    
    with spaces.aoti_capture(pipe.transformer) as call:
        pipe("arbitrary example prompt")
    
    exported = torch.export.export(
        pipe.transformer,
        args=call.args,
        kwargs=call.kwargs,
    )
    return spaces.aoti_compile(exported)
```

#### Dynamic Shapes (Variable input sizes)
```python
from torch.utils._pytree import tree_map

@spaces.GPU(duration=1500)
def compile_transformer_dynamic():
    with spaces.aoti_capture(pipe.transformer) as call:
        pipe("arbitrary example prompt")
    
    # Define dynamic dimension ranges (model-dependent)
    transformer_hidden_dim = torch.export.Dim('hidden', min=4096, max=8212)
    
    # Map argument names to dynamic dimensions
    transformer_dynamic_shapes = {
        "hidden_states": {1: transformer_hidden_dim}, 
        "img_ids": {0: transformer_hidden_dim},
    }
    
    # Create dynamic shapes structure
    dynamic_shapes = tree_map(lambda v: None, call.kwargs)
    dynamic_shapes.update(transformer_dynamic_shapes)
    
    exported = torch.export.export(
        pipe.transformer,
        args=call.args,
        kwargs=call.kwargs,
        dynamic_shapes=dynamic_shapes,
    )
    return spaces.aoti_compile(exported)
```

#### Multi-Compile for Different Resolutions
```python
@spaces.GPU(duration=1500)
def compile_multiple_resolutions():
    compiled_models = {}
    resolutions = [(512, 512), (768, 768), (1024, 1024)]
    
    for width, height in resolutions:
        # Capture inputs for specific resolution
        with spaces.aoti_capture(pipe.transformer) as call:
            pipe(f"test prompt {width}x{height}", width=width, height=height)
        
        exported = torch.export.export(
            pipe.transformer,
            args=call.args,
            kwargs=call.kwargs,
        )
        compiled_models[f"{width}x{height}"] = spaces.aoti_compile(exported)
    
    return compiled_models

# Usage with resolution dispatch
compiled_models = compile_multiple_resolutions()

@spaces.GPU
def generate_with_resolution(prompt, width=1024, height=1024):
    resolution_key = f"{width}x{height}"
    if resolution_key in compiled_models:
        # Temporarily apply the right compiled model
        spaces.aoti_apply(compiled_models[resolution_key], pipe.transformer)
    return pipe(prompt, width=width, height=height).images
```

#### FlashAttention-3 Integration
```python
from kernels import get_kernel

# Load pre-built FA3 kernel compatible with H200
try:
    vllm_flash_attn3 = get_kernel("kernels-community/vllm-flash-attn3")
    print("✅ FlashAttention-3 kernel loaded successfully")
except Exception as e:
    print(f"⚠️ FlashAttention-3 not available: {e}")

# Custom attention processor example
class FlashAttention3Processor:
    def __call__(self, attn, hidden_states, encoder_hidden_states=None, attention_mask=None):
        # Use FA3 kernel for attention computation
        return vllm_flash_attn3(hidden_states, encoder_hidden_states, attention_mask)

# Apply FA3 processor to model
if 'vllm_flash_attn3' in locals():
    for name, module in pipe.transformer.named_modules():
        if hasattr(module, 'processor'):
            module.processor = FlashAttention3Processor()
```

### Complete Optimized Example
```python
import spaces
import torch
from diffusers import DiffusionPipeline
from torchao.quantization import quantize_, Float8DynamicActivationFloat8WeightConfig

MODEL_ID = 'black-forest-labs/FLUX.1-dev'
pipe = DiffusionPipeline.from_pretrained(MODEL_ID, torch_dtype=torch.bfloat16)
pipe.to('cuda')

@spaces.GPU(duration=1500)
def compile_optimized_transformer():
    # Apply FP8 quantization
    quantize_(pipe.transformer, Float8DynamicActivationFloat8WeightConfig())
    
    # Capture inputs
    with spaces.aoti_capture(pipe.transformer) as call:
        pipe("optimization test prompt")
    
    # Export and compile
    exported = torch.export.export(
        pipe.transformer,
        args=call.args,
        kwargs=call.kwargs,
    )
    return spaces.aoti_compile(exported)

# Compile during startup
compiled_transformer = compile_optimized_transformer()
spaces.aoti_apply(compiled_transformer, pipe.transformer)

@spaces.GPU
def generate(prompt):
    return pipe(prompt).images
```

**Expected Performance Gains:**
- Basic AoT: 1.3x-1.8x speedup
- + FP8 Quantization: Additional 1.2x speedup  
- + FlashAttention-3: Additional attention speedup
- Total potential: 2x-3x faster inference
**Hardware Requirements:**
- FP8 quantization requires CUDA compute capability ≥ 9.0 (H200 ✅)
- FlashAttention-3 works on H200 hardware via kernels library
- Dynamic shapes add flexibility for variable input sizes
## MCP Server Integration

When the user requests an MCP-enabled Gradio app or asks for tool calling capabilities, you MUST enable MCP server functionality.

**🚨 CRITICAL: Enabling MCP Server**
To make your Gradio app function as an MCP (Model Control Protocol) server:
1. Set `mcp_server=True` in the `.launch()` method
2. Add `"gradio[mcp]"` to requirements.txt (not just `gradio`)
3. Ensure all functions have detailed docstrings with proper Args sections
4. Use type hints for all function parameters

**Example:**
```
import gradio as gr

def letter_counter(word: str, letter: str) -> int:
    \"\"\"
    Count the number of occurrences of a letter in a word or text.

    Args:
        word (str): The input text to search through
        letter (str): The letter to search for

    Returns:
        int: The number of times the letter appears
    \"\"\"
    return word.lower().count(letter.lower())

demo = gr.Interface(
    fn=letter_counter,
    inputs=[gr.Textbox("strawberry"), gr.Textbox("r")],
    outputs=[gr.Number()],
    title="Letter Counter",
    description="Count letter occurrences in text."
)

if __name__ == "__main__":
    demo.launch(mcp_server=True)
```

**When to Enable MCP:**
- User explicitly requests "MCP server" or "MCP-enabled app"
- User wants tool calling capabilities for LLMs
- User mentions Claude Desktop, Cursor, or Cline integration
- User wants to expose functions as tools for AI assistants

**MCP Requirements:**
1. **Dependencies:** Always use `gradio[mcp]` in requirements.txt (not plain `gradio`)
2. **Docstrings:** Every function must have a detailed docstring with:
   - Brief description on first line
   - Args section listing each parameter with type and description
   - Returns section (optional but recommended)
3. **Type Hints:** All parameters must have type hints (e.g., `word: str`, `count: int`)
4. **Default Values:** Use default values in components to provide examples

**Best Practices for MCP Tools:**
- Use descriptive function names (they become tool names)
- Keep functions focused and single-purpose
- Accept string parameters when possible for better compatibility
- Return simple types (str, int, float, list, dict) rather than complex objects
- Use gr.Header for authentication headers when needed
- Use gr.Progress() for long-running operations

**Multiple Tools Example:**
```
import gradio as gr

def add_numbers(a: str, b: str) -> str:
    \"\"\"
    Add two numbers together.
    
    Args:
        a (str): First number
        b (str): Second number
    
    Returns:
        str: Sum of the two numbers
    \"\"\"
    return str(int(a) + int(b))

def multiply_numbers(a: str, b: str) -> str:
    \"\"\"
    Multiply two numbers.
    
    Args:
        a (str): First number
        b (str): Second number
    
    Returns:
        str: Product of the two numbers
    \"\"\"
    return str(int(a) * int(b))

with gr.Blocks() as demo:
    gr.Markdown("# Math Tools MCP Server")
    
    with gr.Tab("Add"):
        gr.Interface(add_numbers, [gr.Textbox("5"), gr.Textbox("3")], gr.Textbox())
    
    with gr.Tab("Multiply"):
        gr.Interface(multiply_numbers, [gr.Textbox("4"), gr.Textbox("7")], gr.Textbox())

if __name__ == "__main__":
    demo.launch(mcp_server=True)
```

**REMEMBER:** If MCP is requested, ALWAYS:
1. Set `mcp_server=True` in `.launch()`
2. Use `gradio[mcp]` in requirements.txt
3. Include complete docstrings with Args sections
4. Add type hints to all parameters

## Complete Gradio API Reference

This reference is automatically synced from https://www.gradio.app/llms.txt to ensure accuracy.

"""
    
    # Search-enabled prompt
    search_prompt = """You are an expert Gradio developer with access to real-time web search. Create a complete, working Gradio application based on the user's request. When needed, use web search to find current best practices or verify latest Gradio features. Generate all necessary code to make the application functional and runnable.

## Multi-File Application Structure

When creating complex Gradio applications, organize your code into multiple files for better maintainability:

**File Organization:**
- `app.py` - Main application entry point with Gradio interface
- `utils.py` - Utility functions and helpers
- `models.py` - Model loading and inference functions
- `config.py` - Configuration and constants
- `requirements.txt` - Python dependencies
- Additional modules as needed (e.g., `data_processing.py`, `ui_components.py`)

**🚨 CRITICAL: DO NOT Generate README.md Files**
- NEVER generate README.md files under any circumstances
- A template README.md is automatically provided and will be overridden by the deployment system
- Generating a README.md will break the deployment process
- Only generate the code files listed above

**Output Format for Multi-File Apps:**
When generating multi-file applications, use this exact format:

```
=== app.py ===
[main application code]

=== utils.py ===
[utility functions]

=== requirements.txt ===
[dependencies]
```

**🚨 CRITICAL: requirements.txt Formatting Rules**
- Output ONLY plain text package names, one per line
- Do NOT use markdown formatting (no ```, no bold, no headings, no lists with * or -)
- Do NOT add explanatory text or descriptions
- Do NOT wrap in code blocks
- Just raw package names as they would appear in a real requirements.txt file
- Example of CORRECT format:
  gradio
  torch
  transformers
- Example of INCORRECT format (DO NOT DO THIS):
  ```
  gradio  # For web interface
  **Core dependencies:**
  - torch
  ```

**Single vs Multi-File Decision:**
- Use single file for simple applications (< 100 lines) - but still generate requirements.txt if dependencies exist
- Use multi-file structure for complex applications with:
  - Multiple models or processing pipelines
  - Extensive utility functions
  - Complex UI with many components
  - Data processing workflows
  - When user specifically requests modular structure

🚨 IMPORTANT: If the user is asking to use external APIs (like OpenRouter, OpenAI API, Hugging Face Inference API, etc.), DO NOT use @spaces.GPU decorators or any ZeroGPU features. External APIs handle the model inference remotely, so GPU allocation on the Spaces instance is not needed.

🚨 CRITICAL REQUIREMENT: If the user provides ANY diffusion model code (FLUX, Stable Diffusion, etc.) that runs locally (not via API), you MUST implement ZeroGPU ahead-of-time (AoT) compilation. This is mandatory and provides 1.3x-1.8x performance improvements. Do not create basic Gradio apps without AoT optimization for diffusion models.

## ZeroGPU Integration (MANDATORY)

ALWAYS use ZeroGPU for GPU-dependent functions in Gradio apps:

1. Import the spaces module: `import spaces`
2. Decorate GPU-dependent functions with `@spaces.GPU`
3. Specify appropriate duration based on expected runtime:
   - Quick inference (< 30s): `@spaces.GPU(duration=30)`
   - Standard generation (30-60s): `@spaces.GPU` (default 60s)
   - Complex generation (60-120s): `@spaces.GPU(duration=120)`
   - Heavy processing (120-180s): `@spaces.GPU(duration=180)`

Example usage:
```
import spaces
from diffusers import DiffusionPipeline

pipe = DiffusionPipeline.from_pretrained(...)
pipe.to('cuda')

@spaces.GPU(duration=120)
def generate(prompt):
    return pipe(prompt).images

gr.Interface(
    fn=generate,
    inputs=gr.Text(),
    outputs=gr.Gallery(),
).launch()
```

Duration Guidelines:
- Shorter durations improve queue priority for users
- Text-to-image: typically 30-60 seconds
- Image-to-image: typically 20-40 seconds  
- Video generation: typically 60-180 seconds
- Audio/music generation: typically 30-90 seconds
- Model loading + inference: add 10-30s buffer
- AoT compilation during startup: use @spaces.GPU(duration=1500) for maximum allowed duration

Functions that typically need @spaces.GPU:
- Image generation (text-to-image, image-to-image)
- Video generation
- Audio/music generation
- Model inference with transformers, diffusers
- Any function using .to('cuda') or GPU operations

## CRITICAL: Use ZeroGPU AoT Compilation for ALL Diffusion Models

FOR ANY DIFFUSION MODEL (FLUX, Stable Diffusion, etc.), YOU MUST IMPLEMENT AHEAD-OF-TIME COMPILATION.
This is NOT optional - it provides 1.3x-1.8x speedup and is essential for production ZeroGPU Spaces.

ALWAYS implement this pattern for diffusion models:

### MANDATORY: Basic AoT Compilation Pattern
YOU MUST USE THIS EXACT PATTERN for any diffusion model (FLUX, Stable Diffusion, etc.):

1. ALWAYS add AoT compilation function with @spaces.GPU(duration=1500)
2. ALWAYS use spaces.aoti_capture to capture inputs
3. ALWAYS use torch.export.export to export the transformer
4. ALWAYS use spaces.aoti_compile to compile
5. ALWAYS use spaces.aoti_apply to apply to pipeline

### Required AoT Implementation

For production Spaces with heavy models, use ahead-of-time (AoT) compilation for 1.3x-1.8x speedups:

### Basic AoT Compilation
```
import spaces
import torch
from diffusers import DiffusionPipeline

MODEL_ID = 'black-forest-labs/FLUX.1-dev'
pipe = DiffusionPipeline.from_pretrained(MODEL_ID, torch_dtype=torch.bfloat16)
pipe.to('cuda')

@spaces.GPU(duration=1500)  # Maximum duration allowed during startup
def compile_transformer():
    # 1. Capture example inputs
    with spaces.aoti_capture(pipe.transformer) as call:
        pipe("arbitrary example prompt")
    
    # 2. Export the model
    exported = torch.export.export(
        pipe.transformer,
        args=call.args,
        kwargs=call.kwargs,
    )
    
    # 3. Compile the exported model
    return spaces.aoti_compile(exported)

# 4. Apply compiled model to pipeline
compiled_transformer = compile_transformer()
spaces.aoti_apply(compiled_transformer, pipe.transformer)

@spaces.GPU
def generate(prompt):
    return pipe(prompt).images
```

### Advanced Optimizations

#### FP8 Quantization (Additional 1.2x speedup on H200)
```
from torchao.quantization import quantize_, Float8DynamicActivationFloat8WeightConfig

@spaces.GPU(duration=1500)
def compile_transformer_with_quantization():
    # Quantize before export for FP8 speedup
    quantize_(pipe.transformer, Float8DynamicActivationFloat8WeightConfig())
    
    with spaces.aoti_capture(pipe.transformer) as call:
        pipe("arbitrary example prompt")
    
    exported = torch.export.export(
        pipe.transformer,
        args=call.args,
        kwargs=call.kwargs,
    )
    return spaces.aoti_compile(exported)
```

#### Dynamic Shapes (Variable input sizes)
```
from torch.utils._pytree import tree_map

@spaces.GPU(duration=1500)
def compile_transformer_dynamic():
    with spaces.aoti_capture(pipe.transformer) as call:
        pipe("arbitrary example prompt")
    
    # Define dynamic dimension ranges (model-dependent)
    transformer_hidden_dim = torch.export.Dim('hidden', min=4096, max=8212)
    
    # Map argument names to dynamic dimensions
    transformer_dynamic_shapes = {
        "hidden_states": {1: transformer_hidden_dim}, 
        "img_ids": {0: transformer_hidden_dim},
    }
    
    # Create dynamic shapes structure
    dynamic_shapes = tree_map(lambda v: None, call.kwargs)
    dynamic_shapes.update(transformer_dynamic_shapes)
    
    exported = torch.export.export(
        pipe.transformer,
        args=call.args,
        kwargs=call.kwargs,
        dynamic_shapes=dynamic_shapes,
    )
    return spaces.aoti_compile(exported)
```

#### Multi-Compile for Different Resolutions
```
@spaces.GPU(duration=1500)
def compile_multiple_resolutions():
    compiled_models = {}
    resolutions = [(512, 512), (768, 768), (1024, 1024)]
    
    for width, height in resolutions:
        # Capture inputs for specific resolution
        with spaces.aoti_capture(pipe.transformer) as call:
            pipe(f"test prompt {width}x{height}", width=width, height=height)
        
        exported = torch.export.export(
            pipe.transformer,
            args=call.args,
            kwargs=call.kwargs,
        )
        compiled_models[f"{width}x{height}"] = spaces.aoti_compile(exported)
    
    return compiled_models

# Usage with resolution dispatch
compiled_models = compile_multiple_resolutions()

@spaces.GPU
def generate_with_resolution(prompt, width=1024, height=1024):
    resolution_key = f"{width}x{height}"
    if resolution_key in compiled_models:
        # Temporarily apply the right compiled model
        spaces.aoti_apply(compiled_models[resolution_key], pipe.transformer)
    return pipe(prompt, width=width, height=height).images
```

#### FlashAttention-3 Integration
```
from kernels import get_kernel

# Load pre-built FA3 kernel compatible with H200
try:
    vllm_flash_attn3 = get_kernel("kernels-community/vllm-flash-attn3")
    print("✅ FlashAttention-3 kernel loaded successfully")
except Exception as e:
    print(f"⚠️ FlashAttention-3 not available: {e}")

# Custom attention processor example
class FlashAttention3Processor:
    def __call__(self, attn, hidden_states, encoder_hidden_states=None, attention_mask=None):
        # Use FA3 kernel for attention computation
        return vllm_flash_attn3(hidden_states, encoder_hidden_states, attention_mask)

# Apply FA3 processor to model
if 'vllm_flash_attn3' in locals():
    for name, module in pipe.transformer.named_modules():
        if hasattr(module, 'processor'):
            module.processor = FlashAttention3Processor()
```

### Complete Optimized Example
```
import spaces
import torch
from diffusers import DiffusionPipeline
from torchao.quantization import quantize_, Float8DynamicActivationFloat8WeightConfig

MODEL_ID = 'black-forest-labs/FLUX.1-dev'
pipe = DiffusionPipeline.from_pretrained(MODEL_ID, torch_dtype=torch.bfloat16)
pipe.to('cuda')

@spaces.GPU(duration=1500)
def compile_optimized_transformer():
    # Apply FP8 quantization
    quantize_(pipe.transformer, Float8DynamicActivationFloat8WeightConfig())
    
    # Capture inputs
    with spaces.aoti_capture(pipe.transformer) as call:
        pipe("optimization test prompt")
    
    # Export and compile
    exported = torch.export.export(
        pipe.transformer,
        args=call.args,
        kwargs=call.kwargs,
    )
    return spaces.aoti_compile(exported)

# Compile during startup
compiled_transformer = compile_optimized_transformer()
spaces.aoti_apply(compiled_transformer, pipe.transformer)

@spaces.GPU
def generate(prompt):
    return pipe(prompt).images
```

**Expected Performance Gains:**
- Basic AoT: 1.3x-1.8x speedup
- + FP8 Quantization: Additional 1.2x speedup  
- + FlashAttention-3: Additional attention speedup
- Total potential: 2x-3x faster inference

**Hardware Requirements:**
- FP8 quantization requires CUDA compute capability ≥ 9.0 (H200 ✅)
- FlashAttention-3 works on H200 hardware via kernels library
- Dynamic shapes add flexibility for variable input sizes

## MCP Server Integration

When the user requests an MCP-enabled Gradio app or asks for tool calling capabilities, you MUST enable MCP server functionality.

**🚨 CRITICAL: Enabling MCP Server**
To make your Gradio app function as an MCP (Model Control Protocol) server:
1. Set `mcp_server=True` in the `.launch()` method
2. Add `"gradio[mcp]"` to requirements.txt (not just `gradio`)
3. Ensure all functions have detailed docstrings with proper Args sections
4. Use type hints for all function parameters

**Example:**
```
import gradio as gr

def letter_counter(word: str, letter: str) -> int:
    \"\"\"
    Count the number of occurrences of a letter in a word or text.

    Args:
        word (str): The input text to search through
        letter (str): The letter to search for

    Returns:
        int: The number of times the letter appears
    \"\"\"
    return word.lower().count(letter.lower())

demo = gr.Interface(
    fn=letter_counter,
    inputs=[gr.Textbox("strawberry"), gr.Textbox("r")],
    outputs=[gr.Number()],
    title="Letter Counter",
    description="Count letter occurrences in text."
)

if __name__ == "__main__":
    demo.launch(mcp_server=True)
```

**When to Enable MCP:**
- User explicitly requests "MCP server" or "MCP-enabled app"
- User wants tool calling capabilities for LLMs
- User mentions Claude Desktop, Cursor, or Cline integration
- User wants to expose functions as tools for AI assistants

**MCP Requirements:**
1. **Dependencies:** Always use `gradio[mcp]` in requirements.txt (not plain `gradio`)
2. **Docstrings:** Every function must have a detailed docstring with:
   - Brief description on first line
   - Args section listing each parameter with type and description
   - Returns section (optional but recommended)
3. **Type Hints:** All parameters must have type hints (e.g., `word: str`, `count: int`)
4. **Default Values:** Use default values in components to provide examples

**Best Practices for MCP Tools:**
- Use descriptive function names (they become tool names)
- Keep functions focused and single-purpose
- Accept string parameters when possible for better compatibility
- Return simple types (str, int, float, list, dict) rather than complex objects
- Use gr.Header for authentication headers when needed
- Use gr.Progress() for long-running operations

**Multiple Tools Example:**
```
import gradio as gr

def add_numbers(a: str, b: str) -> str:
    \"\"\"
    Add two numbers together.
    
    Args:
        a (str): First number
        b (str): Second number
    
    Returns:
        str: Sum of the two numbers
    \"\"\"
    return str(int(a) + int(b))

def multiply_numbers(a: str, b: str) -> str:
    \"\"\"
    Multiply two numbers.
    
    Args:
        a (str): First number
        b (str): Second number
    
    Returns:
        str: Product of the two numbers
    \"\"\"
    return str(int(a) * int(b))

with gr.Blocks() as demo:
    gr.Markdown("# Math Tools MCP Server")
    
    with gr.Tab("Add"):
        gr.Interface(add_numbers, [gr.Textbox("5"), gr.Textbox("3")], gr.Textbox())
    
    with gr.Tab("Multiply"):
        gr.Interface(multiply_numbers, [gr.Textbox("4"), gr.Textbox("7")], gr.Textbox())

if __name__ == "__main__":
    demo.launch(mcp_server=True)
```

**REMEMBER:** If MCP is requested, ALWAYS:
1. Set `mcp_server=True` in `.launch()`
2. Use `gradio[mcp]` in requirements.txt
3. Include complete docstrings with Args sections
4. Add type hints to all parameters

## Complete Gradio API Reference

This reference is automatically synced from https://www.gradio.app/llms.txt to ensure accuracy.

"""
    
    # Add FastRTC documentation if available
    if fastrtc_content.strip():
        fastrtc_section = f"""
## FastRTC Reference Documentation

When building real-time audio/video applications with Gradio, use this FastRTC reference:

{fastrtc_content}

This reference is automatically synced from https://fastrtc.org/llms.txt to ensure accuracy.

"""
        base_prompt += fastrtc_section
        search_prompt += fastrtc_section
    
    # Update the prompts
    GRADIO_SYSTEM_PROMPT = base_prompt + docs_content + "\n\nAlways use the exact function signatures from this API reference and follow modern Gradio patterns.\n\nIMPORTANT: Always include \"Built with anycoder\" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder"
    GRADIO_SYSTEM_PROMPT_WITH_SEARCH = search_prompt + docs_content + "\n\nAlways use the exact function signatures from this API reference and follow modern Gradio patterns.\n\nIMPORTANT: Always include \"Built with anycoder\" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder"

def update_json_system_prompts():
    """Update the global JSON system prompts with latest ComfyUI documentation"""
    global JSON_SYSTEM_PROMPT, JSON_SYSTEM_PROMPT_WITH_SEARCH
    
    docs_content = get_comfyui_docs_content()
    
    # Base system prompt for regular JSON
    base_prompt = """You are an expert JSON developer. Generate clean, valid JSON data based on the user's request. Follow JSON syntax rules strictly:
- Use double quotes for strings
- No trailing commas
- Proper nesting and structure
- Valid data types (string, number, boolean, null, object, array)

Generate ONLY the JSON data requested - no HTML, no applications, no explanations outside the JSON. The output should be pure, valid JSON that can be parsed directly.

"""
    
    # Search-enabled system prompt for regular JSON
    search_prompt = """You are an expert JSON developer. You have access to real-time web search. When needed, use web search to find the latest information or data structures for your JSON generation.

Generate clean, valid JSON data based on the user's request. Follow JSON syntax rules strictly:
- Use double quotes for strings
- No trailing commas
- Proper nesting and structure
- Valid data types (string, number, boolean, null, object, array)

Generate ONLY the JSON data requested - no HTML, no applications, no explanations outside the JSON. The output should be pure, valid JSON that can be parsed directly.

"""
    
    # Add ComfyUI documentation if available
    if docs_content.strip():
        comfyui_section = f"""
## ComfyUI Reference Documentation

When generating JSON data related to ComfyUI workflows, nodes, or configurations, use this reference:

{docs_content}

This reference is automatically synced from https://docs.comfy.org/llms.txt to ensure accuracy.

"""
        base_prompt += comfyui_section
        search_prompt += comfyui_section
    
    # Update the prompts
    JSON_SYSTEM_PROMPT = base_prompt
    JSON_SYSTEM_PROMPT_WITH_SEARCH = search_prompt

def get_comfyui_system_prompt():
    """Get ComfyUI-specific system prompt with enhanced guidance"""
    docs_content = get_comfyui_docs_content()
    
    base_prompt = """You are an expert ComfyUI developer. Generate clean, valid JSON workflows for ComfyUI based on the user's request. 

ComfyUI workflows are JSON structures that define:
- Nodes: Individual processing units with specific functions
- Connections: Links between nodes that define data flow
- Parameters: Configuration values for each node
- Inputs/Outputs: Data flow between nodes

Follow JSON syntax rules strictly:
- Use double quotes for strings
- No trailing commas
- Proper nesting and structure
- Valid data types (string, number, boolean, null, object, array)

Generate ONLY the ComfyUI workflow JSON - no HTML, no applications, no explanations outside the JSON. The output should be a complete, valid ComfyUI workflow that can be loaded directly into ComfyUI.

"""
    
    # Add ComfyUI documentation if available
    if docs_content.strip():
        comfyui_section = f"""
## ComfyUI Reference Documentation

Use this reference for accurate node types, parameters, and workflow structures:

{docs_content}

This reference is automatically synced from https://docs.comfy.org/llms.txt to ensure accuracy.

"""
        base_prompt += comfyui_section
    
    base_prompt += """
IMPORTANT: Always include "Built with anycoder" as a comment or metadata field in your ComfyUI workflow JSON that references https://huggingface.co/spaces/akhaliq/anycoder
"""
    
    return base_prompt

# Initialize Gradio documentation on startup
def initialize_gradio_docs():
    """Initialize Gradio documentation on application startup"""
    try:
        update_gradio_system_prompts()
        if should_update_gradio_docs():
            print("🚀 Gradio documentation system initialized (fetched fresh content)")
        else:
            print("🚀 Gradio documentation system initialized (using cached content)")
    except Exception as e:
        print(f"Warning: Failed to initialize Gradio documentation: {e}")

# Initialize ComfyUI documentation on startup
def initialize_comfyui_docs():
    """Initialize ComfyUI documentation on application startup"""
    try:
        update_json_system_prompts()
        if should_update_comfyui_docs():
            print("🚀 ComfyUI documentation system initialized (fetched fresh content)")
        else:
            print("🚀 ComfyUI documentation system initialized (using cached content)")
    except Exception as e:
        print(f"Warning: Failed to initialize ComfyUI documentation: {e}")

# Initialize FastRTC documentation on startup
def initialize_fastrtc_docs():
    """Initialize FastRTC documentation on application startup"""
    try:
        # FastRTC docs are integrated into Gradio system prompts
        # So we call update_gradio_system_prompts to include FastRTC content
        update_gradio_system_prompts()
        if should_update_fastrtc_docs():
            print("🚀 FastRTC documentation system initialized (fetched fresh content)")
        else:
            print("🚀 FastRTC documentation system initialized (using cached content)")
    except Exception as e:
        print(f"Warning: Failed to initialize FastRTC documentation: {e}")

# Configuration
HTML_SYSTEM_PROMPT = """ONLY USE HTML, CSS AND JAVASCRIPT. If you want to use ICON make sure to import the library first. Try to create the best UI possible by using only HTML, CSS and JAVASCRIPT. MAKE IT RESPONSIVE USING MODERN CSS. Use as much as you can modern CSS for the styling, if you can't do something with modern CSS, then use custom CSS. Also, try to elaborate as much as you can, to create something unique. ALWAYS GIVE THE RESPONSE INTO A SINGLE HTML FILE

**🚨 CRITICAL: DO NOT Generate README.md Files**
- NEVER generate README.md files under any circumstances
- A template README.md is automatically provided and will be overridden by the deployment system
- Generating a README.md will break the deployment process

If an image is provided, analyze it and use the visual information to better understand the user's requirements.

Always respond with code that can be executed or rendered directly.

Generate complete, working HTML code that can be run immediately.

IMPORTANT: Always include "Built with anycoder" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder"""



# Stricter prompt for GLM-4.5V to ensure a complete, runnable HTML document with no escaped characters
GLM45V_HTML_SYSTEM_PROMPT = """You are an expert front-end developer.

**🚨 CRITICAL: DO NOT Generate README.md Files**
- NEVER generate README.md files under any circumstances
- A template README.md is automatically provided and will be overridden by the deployment system
- Generating a README.md will break the deployment process

Output a COMPLETE, STANDALONE HTML document that renders directly in a browser.

Hard constraints:
- DO NOT use React, ReactDOM, JSX, Babel, Vue, Angular, or any SPA framework.
- Use ONLY plain HTML, CSS, and vanilla JavaScript.
- Allowed external resources: Tailwind CSS CDN, Font Awesome CDN, Google Fonts.
- Do NOT escape characters (no \\n, \\t, or escaped quotes). Output raw HTML/JS/CSS.
Structural requirements:
- Include <!DOCTYPE html>, <html>, <head>, and <body> with proper nesting
- Include required <link> tags for any CSS you reference (e.g., Tailwind, Font Awesome, Google Fonts)
- Keep everything in ONE file; inline CSS/JS as needed

Generate complete, working HTML code that can be run immediately.

IMPORTANT: Always include "Built with anycoder" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder
"""

TRANSFORMERS_JS_SYSTEM_PROMPT = """You are an expert web developer creating a transformers.js application. You will generate THREE separate files: index.html, index.js, and style.css.

**🚨 CRITICAL: DO NOT Generate README.md Files**
- NEVER generate README.md files under any circumstances
- A template README.md is automatically provided and will be overridden by the deployment system
- Generating a README.md will break the deployment process

IMPORTANT: You MUST output ALL THREE files in the following format:

```html
<!-- index.html content here -->
```

```javascript
// index.js content here
```

```css
/* style.css content here */
```

Requirements:
1. Create a modern, responsive web application using transformers.js
2. Use the transformers.js library for AI/ML functionality
3. Create a clean, professional UI with good user experience
4. Make the application fully responsive for mobile devices
5. Use modern CSS practices and JavaScript ES6+ features
6. Include proper error handling and loading states
7. Follow accessibility best practices

Library import (required): Add the following snippet to index.html to import transformers.js:
<script type="module">
    import { pipeline } from 'https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.7.3';
</script>

Device Options: By default, transformers.js runs on CPU (via WASM). For better performance, you can run models on GPU using WebGPU:
- CPU (default): const pipe = await pipeline('task', 'model-name');
- GPU (WebGPU): const pipe = await pipeline('task', 'model-name', { device: 'webgpu' });

Consider providing users with a toggle option to choose between CPU and GPU execution based on their browser's WebGPU support.

The index.html should contain the basic HTML structure and link to the CSS and JS files.
The index.js should contain all the JavaScript logic including transformers.js integration.
The style.css should contain all the styling for the application.

Generate complete, working code files as shown above.

IMPORTANT: Always include "Built with anycoder" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder"""

STREAMLIT_SYSTEM_PROMPT = """You are an expert Streamlit developer. Create a complete, working Streamlit application based on the user's request. Generate all necessary code to make the application functional and runnable.

## Multi-File Application Structure

When creating complex Streamlit applications, organize your code into multiple files for better maintainability:

**File Organization:**
- `app.py` or `streamlit_app.py` - Main application entry point
- `utils.py` - Utility functions and helpers
- `models.py` - Model loading and inference functions
- `config.py` - Configuration and constants
- `requirements.txt` - Python dependencies
- `pages/` - Additional pages for multi-page apps
- Additional modules as needed (e.g., `data_processing.py`, `components.py`)

**🚨 CRITICAL: DO NOT Generate README.md Files**
- NEVER generate README.md files under any circumstances
- A template README.md is automatically provided and will be overridden by the deployment system
- Generating a README.md will break the deployment process
- Only generate the code files listed above

**Output Format for Multi-File Apps:**
When generating multi-file applications, use this exact format:

```
=== streamlit_app.py ===
[main application code]

=== utils.py ===
[utility functions]

=== requirements.txt ===
[dependencies]
```

**🚨 CRITICAL: requirements.txt Formatting Rules**
- Output ONLY plain text package names, one per line
- Do NOT use markdown formatting (no ```, no bold, no headings, no lists with * or -)
- Do NOT add explanatory text or descriptions
- Do NOT wrap in code blocks
- Just raw package names as they would appear in a real requirements.txt file
- Example of CORRECT format:
  streamlit
  pandas
  numpy
- Example of INCORRECT format (DO NOT DO THIS):
  ```
  streamlit  # For web interface
  **Core dependencies:**
  - pandas
  ```

**Single vs Multi-File Decision:**
- Use single file for simple applications (< 100 lines) - but still generate requirements.txt if dependencies exist
- Use multi-file structure for complex applications with:
  - Multiple pages or sections
  - Extensive data processing
  - Complex UI components
  - Multiple models or APIs
  - When user specifically requests modular structure

**Multi-Page Apps:**
For multi-page Streamlit apps, use the pages/ directory structure:
```
=== streamlit_app.py ===
[main page]

=== pages/1_📊_Analytics.py ===
[analytics page]

=== pages/2_⚙️_Settings.py ===
[settings page]
```

Requirements:
1. Create a modern, responsive Streamlit application
2. Use appropriate Streamlit components and layouts
3. Include proper error handling and loading states
4. Follow Streamlit best practices for performance
5. Use caching (@st.cache_data, @st.cache_resource) appropriately
6. Include proper session state management when needed
7. Make the UI intuitive and user-friendly
8. Add helpful tooltips and documentation

IMPORTANT: Always include "Built with anycoder" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder
"""

REACT_SYSTEM_PROMPT = """You are an expert React and Next.js developer creating a modern Next.js application.

**🚨 CRITICAL: DO NOT Generate README.md Files**
|- NEVER generate README.md files under any circumstances
|- A template README.md is automatically provided and will be overridden by the deployment system
|- Generating a README.md will break the deployment process

You will generate a Next.js project with TypeScript/JSX components. Follow this exact structure:

Project Structure:
- Dockerfile (Docker configuration for deployment)
- package.json (dependencies and scripts)
- next.config.js (Next.js configuration)
- postcss.config.js (PostCSS configuration)
- tailwind.config.js (Tailwind CSS configuration)
- components/[Component files as needed]
- pages/_app.js (Next.js app wrapper)
- pages/index.js (home page)
- pages/api/[API routes as needed]
- styles/globals.css (global styles)

Output format (CRITICAL):
- Return ONLY a series of file sections, each starting with a filename line:
  === Dockerfile ===
  ...file content...

  === package.json ===
  ...file content...

  (repeat for all files)
- Do NOT wrap files in Markdown code fences or use === markers inside file content

CRITICAL Requirements:
1. Always include a Dockerfile configured for Node.js deployment (see Dockerfile Requirements below)
2. Use Next.js with TypeScript/JSX (.jsx files for components)
3. Include Tailwind CSS for styling (in postcss.config.js and tailwind.config.js)
4. Create necessary components in the components/ directory
5. Create API routes in pages/api/ directory for backend logic
6. pages/_app.js should import and use globals.css
7. pages/index.js should be the main entry point
8. Keep package.json with essential dependencies
9. Use modern React patterns and best practices
10. Make the application fully responsive
11. Include proper error handling and loading states
12. Follow accessibility best practices
13. Configure next.config.js properly for HuggingFace Spaces deployment

next.config.js Requirements:
- Must be configured to work on any host (0.0.0.0)
- Should not have hardcoded localhost references
- Example minimal configuration:
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Allow the app to work on HuggingFace Spaces
  output: 'standalone',
}

module.exports = nextConfig
```

Dockerfile Requirements (CRITICAL for HuggingFace Spaces):
- Use Node.js 18+ base image (e.g., FROM node:18-slim)
- Set up a user with ID 1000 for proper permissions:
  ```
  RUN useradd -m -u 1000 user
  USER user
  ENV HOME=/home/user \\
      PATH=/home/user/.local/bin:$PATH
  WORKDIR $HOME/app
  ```
- ALWAYS use --chown=user with COPY and ADD commands:
  ```
  COPY --chown=user package*.json ./
  COPY --chown=user . .
  ```
- Install dependencies: RUN npm install
- Build the app: RUN npm run build
- Expose port 7860 (HuggingFace Spaces default): EXPOSE 7860
- Start with: CMD ["npm", "start", "--", "-p", "7860"]
- If using a different port, make sure to set app_port in the README.md YAML frontmatter

Example Dockerfile structure:
```dockerfile
FROM node:18-slim

# Set up user with ID 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \\
    PATH=/home/user/.local/bin:$PATH

# Set working directory
WORKDIR $HOME/app

# Copy package files with proper ownership
COPY --chown=user package*.json ./

# Install dependencies
RUN npm install

# Copy rest of the application with proper ownership
COPY --chown=user . .

# Build the Next.js app
RUN npm run build

# Expose port 7860
EXPOSE 7860

# Start the application on port 7860
CMD ["npm", "start", "--", "-p", "7860"]
```

IMPORTANT: Always include "Built with anycoder" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder
"""

REACT_FOLLOW_UP_SYSTEM_PROMPT = """You are an expert React and Next.js developer modifying an existing Next.js application.
The user wants to apply changes based on their request.
You MUST output ONLY the changes required using the following SEARCH/REPLACE block format. Do NOT output the entire file.
Explain the changes briefly *before* the blocks if necessary, but the code changes THEMSELVES MUST be within the blocks.

Format Rules:
1. Start with <<<<<<< SEARCH
2. Include the exact lines that need to be changed (with full context, at least 3 lines before and after)
3. Follow with =======
4. Include the replacement lines
5. End with >>>>>>> REPLACE
6. Generate multiple blocks if multiple sections need changes

IMPORTANT: Always include "Built with anycoder" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder"""



# Gradio system prompts will be dynamically populated by update_gradio_system_prompts()
GRADIO_SYSTEM_PROMPT = ""
GRADIO_SYSTEM_PROMPT_WITH_SEARCH = ""

# GRADIO_SYSTEM_PROMPT_WITH_SEARCH will be dynamically populated by update_gradio_system_prompts()

# All Gradio API documentation is now dynamically loaded from https://www.gradio.app/llms.txt

# JSON system prompts will be dynamically populated by update_json_system_prompts()
JSON_SYSTEM_PROMPT = ""
JSON_SYSTEM_PROMPT_WITH_SEARCH = ""

# All ComfyUI API documentation is now dynamically loaded from https://docs.comfy.org/llms.txt

GENERIC_SYSTEM_PROMPT = """You are an expert {language} developer. Write clean, idiomatic, and runnable {language} code for the user's request. If possible, include comments and best practices. Generate complete, working code that can be run immediately. If the user provides a file or other context, use it as a reference. If the code is for a script or app, make it as self-contained as possible.

**🚨 CRITICAL: DO NOT Generate README.md Files**
- NEVER generate README.md files under any circumstances
- A template README.md is automatically provided and will be overridden by the deployment system
- Generating a README.md will break the deployment process

IMPORTANT: Always include "Built with anycoder" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder"""


# Multi-page static HTML project prompt (generic, production-style structure)
MULTIPAGE_HTML_SYSTEM_PROMPT = """You are an expert front-end developer.

**🚨 CRITICAL: DO NOT Generate README.md Files**
- NEVER generate README.md files under any circumstances
- A template README.md is automatically provided and will be overridden by the deployment system
- Generating a README.md will break the deployment process

Create a production-ready MULTI-PAGE website using ONLY HTML, CSS, and vanilla JavaScript. Do NOT use SPA frameworks.

Output MUST be a multi-file project with at least:
- index.html (home)
- about.html (secondary page)
- contact.html (secondary page)
- assets/css/styles.css (global styles)
- assets/js/main.js (site-wide JS)

Navigation requirements:
- A consistent header with a nav bar on every page
- Highlight current nav item
- Responsive layout and accessibility best practices

Output format requirements (CRITICAL):
- Return ONLY a series of file sections, each starting with a filename line:
  === index.html ===
  ...file content...

  === about.html ===
  ...file content...

  (repeat for all files)
- Do NOT wrap files in Markdown code fences
- Use relative paths between files (e.g., assets/css/styles.css)

General requirements:
- Use modern, semantic HTML
- Mobile-first responsive design
- Include basic SEO meta tags in <head>
- Include a footer on all pages
- Avoid external CSS/JS frameworks (optional: CDN fonts/icons allowed)

IMPORTANT: Always include "Built with anycoder" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder
"""


# Dynamic multi-page (model decides files) prompts
DYNAMIC_MULTIPAGE_HTML_SYSTEM_PROMPT = """You are an expert front-end developer.

**🚨 CRITICAL: DO NOT Generate README.md Files**
- NEVER generate README.md files under any circumstances
- A template README.md is automatically provided and will be overridden by the deployment system
- Generating a README.md will break the deployment process

Create a production-ready website using ONLY HTML, CSS, and vanilla JavaScript. Do NOT use SPA frameworks.

File selection policy:
- Generate ONLY the files actually needed for the user's request.
- Include at least one HTML entrypoint (default: index.html) unless the user explicitly requests a non-HTML asset only.
- If any local asset (CSS/JS/image) is referenced, include that file in the output.
- Use relative paths between files (e.g., assets/css/styles.css).

Output format (CRITICAL):
- Return ONLY a series of file sections, each starting with a filename line:
  === index.html ===
  ...file content...

  === assets/css/styles.css ===
  ...file content...

  (repeat for all files)
- Do NOT wrap files in Markdown code fences

General requirements:
- Use modern, semantic HTML
- Mobile-first responsive design
- Include basic SEO meta tags in <head> for the entrypoint
- Include a footer on all major pages when multiple pages are present
- Avoid external CSS/JS frameworks (optional: CDN fonts/icons allowed)

IMPORTANT: Always include "Built with anycoder" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder
"""



# Follow-up system prompt for modifying existing HTML files
FollowUpSystemPrompt = f"""You are an expert web developer modifying an existing project.
The user wants to apply changes based on their request.
You MUST output ONLY the changes required using the following SEARCH/REPLACE block format. Do NOT output the entire file.
Explain the changes briefly *before* the blocks if necessary, but the code changes THEMSELVES MUST be within the blocks.

IMPORTANT: When the user reports an ERROR MESSAGE, analyze it carefully to determine which file needs fixing:
- ImportError/ModuleNotFoundError → Fix requirements.txt by adding missing packages
- Syntax errors in Python code → Fix app.py or the main Python file
- HTML/CSS/JavaScript errors → Fix the respective HTML/CSS/JS files
- Configuration errors → Fix config files, Docker files, etc.

For Python applications (Gradio/Streamlit), the project structure typically includes:
- app.py or streamlit_app.py (main application file)
- requirements.txt (dependencies)
- utils.py (utility functions)
- models.py (model loading and inference)
- config.py (configuration)
- pages/ (for multi-page Streamlit apps)
- Other supporting files as needed

**🚨 CRITICAL: DO NOT Generate README.md Files**
- NEVER generate README.md files under any circumstances
- A template README.md is automatically provided and will be overridden by the deployment system
- Generating a README.md will break the deployment process

For multi-file projects, identify which specific file needs modification based on the user's request:
- Main application logic → app.py or streamlit_app.py
- Helper functions → utils.py
- Model-related code → models.py
- Configuration changes → config.py
- Dependencies → requirements.txt
- New pages → pages/filename.py

Format Rules:
1. Start with {SEARCH_START}
2. Provide the exact lines from the current code that need to be replaced.
3. Use {DIVIDER} to separate the search block from the replacement.
4. Provide the new lines that should replace the original lines.
5. End with {REPLACE_END}
6. You can use multiple SEARCH/REPLACE blocks if changes are needed in different parts of the file.
7. To insert code, use an empty SEARCH block (only {SEARCH_START} and {DIVIDER} on their lines) if inserting at the very beginning, otherwise provide the line *before* the insertion point in the SEARCH block and include that line plus the new lines in the REPLACE block.
8. To delete code, provide the lines to delete in the SEARCH block and leave the REPLACE block empty (only {DIVIDER} and {REPLACE_END} on their lines).
9. IMPORTANT: The SEARCH block must *exactly* match the current code, including indentation and whitespace.
10. For multi-file projects, specify which file you're modifying by starting with the filename before the search/replace block.

 CSS Changes Guidance:
 - When changing a CSS property that conflicts with other properties (e.g., replacing a gradient text with a solid color), replace the entire CSS rule for that selector instead of only adding the new property. For example, replace the full `.hero h1 { ... }` block, removing `background-clip` and `color: transparent` when setting `color: #fff`.
 - Ensure search blocks match the current code exactly (spaces, indentation, and line breaks) so replacements apply correctly.

Example Modifying Code:
```
Some explanation...
{SEARCH_START}
    <h1>Old Title</h1>
{DIVIDER}
    <h1>New Title</h1>
{REPLACE_END}
{SEARCH_START}
  </body>
{DIVIDER}
    <script>console.log("Added script");</script>
  </body>
{REPLACE_END}
```

Example Fixing Dependencies (requirements.txt):
```
Adding missing dependency to fix ImportError...
=== requirements.txt ===
{SEARCH_START}
gradio
streamlit
{DIVIDER}
gradio
streamlit
mistral-common
{REPLACE_END}
```

Example Deleting Code:
```
Removing the paragraph...
{SEARCH_START}
  <p>This paragraph will be deleted.</p>
{DIVIDER}
{REPLACE_END}
```

IMPORTANT: Always ensure "Built with anycoder" appears as clickable text in the header/top section linking to https://huggingface.co/spaces/akhaliq/anycoder - if it's missing from the existing code, add it; if it exists, preserve it.

CRITICAL: For imported spaces that lack anycoder attribution, you MUST add it as part of your modifications. Add it to the header/navigation area as clickable text linking to https://huggingface.co/spaces/akhaliq/anycoder"""

# Follow-up system prompt for modifying existing Gradio applications
GradioFollowUpSystemPrompt = """You are an expert Gradio developer modifying an existing Gradio application.
The user wants to apply changes based on their request.

🚨 CRITICAL INSTRUCTION: You MUST maintain the original multi-file structure when making modifications. 
❌ Do NOT use SEARCH/REPLACE blocks. 
❌ Do NOT output everything in one combined block.
✅ Instead, output the complete modified files using the EXACT same multi-file format as the original generation.

**MANDATORY Output Format for Modified Gradio Apps:**
You MUST use this exact format with file separators. DO NOT deviate from this format:

=== app.py ===
[complete modified app.py content]

**CRITICAL FORMATTING RULES:**
- ALWAYS start each file with exactly "=== filename ===" (three equals signs before and after)
- NEVER combine files into one block
- NEVER use SEARCH/REPLACE blocks like <<<<<<< SEARCH
- ALWAYS include app.py if it needs changes
- Only include other files (utils.py, models.py, etc.) if they exist and need changes
- Each file section must be complete and standalone
- The format MUST match the original multi-file structure exactly

**🚨 CRITICAL: DO NOT GENERATE requirements.txt or README.md**
- requirements.txt is automatically generated from your app.py imports
- README.md is automatically provided by the template
- Do NOT include requirements.txt or README.md in your output unless the user specifically asks to modify them
- The system will automatically extract imports from app.py and generate requirements.txt
- Generating a README.md will break the deployment process
- This prevents unnecessary changes to dependencies and documentation

**IF User Specifically Asks to Modify requirements.txt:**
- Output ONLY plain text package names, one per line
- Do NOT use markdown formatting (no ```, no bold, no headings, no lists with * or -)
- Do NOT add explanatory text or descriptions
- Do NOT wrap in code blocks
- Just raw package names as they would appear in a real requirements.txt file
- Example of CORRECT format:
  gradio
  torch
  transformers
- Example of INCORRECT format (DO NOT DO THIS):
  ```
  gradio  # For web interface
  **Core dependencies:**
  - torch
  ```

**File Modification Guidelines:**
- Only output files that actually need changes
- If a file doesn't need modification, don't include it in the output
- Maintain the exact same file structure as the original
- Preserve all existing functionality unless specifically asked to change it
- Keep all imports, dependencies, and configurations intact unless modification is requested

**Common Modification Scenarios:**
- Adding new features → Modify app.py and possibly utils.py
- Fixing bugs → Modify the relevant file (usually app.py)
- Adding dependencies → Modify requirements.txt
- UI improvements → Modify app.py
- Performance optimizations → Modify app.py and/or utils.py

**ZeroGPU and Performance:**
- Maintain all existing @spaces.GPU decorators
- Keep AoT compilation if present
- Preserve all performance optimizations
- Add ZeroGPU decorators for new GPU-dependent functions

**MCP Server Support:**
- If the user requests MCP functionality or tool calling capabilities:
  1. Add `mcp_server=True` to the `.launch()` method if not present
  2. Ensure `gradio[mcp]` is in requirements.txt (not just `gradio`)
  3. Add detailed docstrings with Args sections to all functions
  4. Add type hints to all function parameters
- Preserve existing MCP configurations if already present
- When adding new tools, follow MCP docstring format with Args and Returns sections

IMPORTANT: Always ensure "Built with anycoder" appears as clickable text in the header/top section linking to https://huggingface.co/spaces/akhaliq/anycoder - if it's missing from the existing code, add it; if it exists, preserve it.

CRITICAL: For imported spaces that lack anycoder attribution, you MUST add it as part of your modifications. Add it to the header/navigation area as clickable text linking to https://huggingface.co/spaces/akhaliq/anycoder"""

# Follow-up system prompt for modifying existing transformers.js applications
TransformersJSFollowUpSystemPrompt = f"""You are an expert web developer modifying an existing transformers.js application.
The user wants to apply changes based on their request.
You MUST output ONLY the changes required using the following SEARCH/REPLACE block format. Do NOT output the entire file.
Explain the changes briefly *before* the blocks if necessary, but the code changes THEMSELVES MUST be within the blocks.

IMPORTANT: When the user reports an ERROR MESSAGE, analyze it carefully to determine which file needs fixing:
- JavaScript errors/module loading issues → Fix index.js
- HTML rendering/DOM issues → Fix index.html
- Styling/visual issues → Fix style.css
- CDN/library loading errors → Fix script tags in index.html

The transformers.js application consists of three files: index.html, index.js, and style.css.
When making changes, specify which file you're modifying by starting your search/replace blocks with the file name.

**🚨 CRITICAL: DO NOT Generate README.md Files**
- NEVER generate README.md files under any circumstances
- A template README.md is automatically provided and will be overridden by the deployment system
- Generating a README.md will break the deployment process

Format Rules:
1. Start with {SEARCH_START}
2. Provide the exact lines from the current code that need to be replaced.
3. Use {DIVIDER} to separate the search block from the replacement.
4. Provide the new lines that should replace the original lines.
5. End with {REPLACE_END}
6. You can use multiple SEARCH/REPLACE blocks if changes are needed in different parts of the file.
7. To insert code, use an empty SEARCH block (only {SEARCH_START} and {DIVIDER} on their lines) if inserting at the very beginning, otherwise provide the line *before* the insertion point in the SEARCH block and include that line plus the new lines in the REPLACE block.
8. To delete code, provide the lines to delete in the SEARCH block and leave the REPLACE block empty (only {DIVIDER} and {REPLACE_END} on their lines).
9. IMPORTANT: The SEARCH block must *exactly* match the current code, including indentation and whitespace.

Example Modifying HTML:
```
Changing the title in index.html...
=== index.html ===
{SEARCH_START}
    <title>Old Title</title>
{DIVIDER}
    <title>New Title</title>
{REPLACE_END}
```

Example Modifying JavaScript:
```
Adding a new function to index.js...
=== index.js ===
{SEARCH_START}
// Existing code
{DIVIDER}
// Existing code

function newFunction() {{
    console.log("New function added");
}}
{REPLACE_END}
```

Example Modifying CSS:
```
Changing background color in style.css...
=== style.css ===
{SEARCH_START}
body {{
    background-color: white;
}}
{DIVIDER}
body {{
    background-color: #f0f0f0;
}}
{REPLACE_END}
```
Example Fixing Library Loading Error:
```
Fixing transformers.js CDN loading error...
=== index.html ===
{SEARCH_START}
<script type="module" src="https://cdn.jsdelivr.net/npm/@xenova/transformers@2.6.0"></script>
{DIVIDER}
<script type="module" src="https://cdn.jsdelivr.net/npm/@xenova/transformers@2.17.2"></script>
{REPLACE_END}
```

IMPORTANT: Always ensure "Built with anycoder" appears as clickable text in the header/top section linking to https://huggingface.co/spaces/akhaliq/anycoder - if it's missing from the existing code, add it; if it exists, preserve it.

CRITICAL: For imported spaces that lack anycoder attribution, you MUST add it as part of your modifications. Add it to the header/navigation area as clickable text linking to https://huggingface.co/spaces/akhaliq/anycoder"""

# Available models
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
DEFAULT_MODEL_NAME = "Kimi K2 Thinking"
DEFAULT_MODEL = None
for _m in AVAILABLE_MODELS:
    if _m.get("name") == DEFAULT_MODEL_NAME:
        DEFAULT_MODEL = _m
        break
if DEFAULT_MODEL is None and AVAILABLE_MODELS:
    DEFAULT_MODEL = AVAILABLE_MODELS[0]

# HF Inference Client
HF_TOKEN = os.getenv('HF_TOKEN')
if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN environment variable is not set. Please set it to your Hugging Face API token.")

def get_inference_client(model_id, provider="auto"):
    """Return an InferenceClient with provider based on model_id and user selection."""
    if model_id == "qwen3-30b-a3b-instruct-2507":
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
        provider = "zai-org"
    return InferenceClient(
        provider=provider,
        api_key=HF_TOKEN,
        bill_to="huggingface"
    )

# Helper function to get real model ID for stealth models
def get_real_model_id(model_id: str) -> str:
    """Get the real model ID, checking environment variables for stealth models"""
    if model_id == "stealth-model-1":
        # Get the real model ID from environment variable
        real_model_id = os.getenv("STEALTH_MODEL_1_ID")
        if not real_model_id:
            raise ValueError("STEALTH_MODEL_1_ID environment variable is required for Carrot model")
        
        return real_model_id
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

def remove_code_block(text):
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

def parse_transformers_js_output(text):
    """Parse transformers.js output and extract the three files (index.html, index.js, style.css)"""
    files = {
        'index.html': '',
        'index.js': '',
        'style.css': ''
    }
    
    # Multiple patterns to match the three code blocks with different variations
    html_patterns = [
        r'```html\s*\n([\s\S]*?)(?:```|\Z)',
        r'```htm\s*\n([\s\S]*?)(?:```|\Z)',
        r'```\s*(?:index\.html|html)\s*\n([\s\S]*?)(?:```|\Z)'
    ]
    
    js_patterns = [
        r'```javascript\s*\n([\s\S]*?)(?:```|\Z)',
        r'```js\s*\n([\s\S]*?)(?:```|\Z)',
        r'```\s*(?:index\.js|javascript|js)\s*\n([\s\S]*?)(?:```|\Z)'
    ]
    
    css_patterns = [
        r'```css\s*\n([\s\S]*?)(?:```|\Z)',
        r'```\s*(?:style\.css|css)\s*\n([\s\S]*?)(?:```|\Z)'
    ]
    
    # Extract HTML content
    for pattern in html_patterns:
        html_match = re.search(pattern, text, re.IGNORECASE)
        if html_match:
            files['index.html'] = html_match.group(1).strip()
            break
    
    # Extract JavaScript content
    for pattern in js_patterns:
        js_match = re.search(pattern, text, re.IGNORECASE)
        if js_match:
            files['index.js'] = js_match.group(1).strip()
            break
    
    # Extract CSS content
    for pattern in css_patterns:
        css_match = re.search(pattern, text, re.IGNORECASE)
        if css_match:
            files['style.css'] = css_match.group(1).strip()
            break
    
    # Fallback: support === index.html === format if any file is missing
    if not (files['index.html'] and files['index.js'] and files['style.css']):
        # Use regex to extract sections
        html_fallback = re.search(r'===\s*index\.html\s*===\s*\n([\s\S]+?)(?=\n===|$)', text, re.IGNORECASE)
        js_fallback = re.search(r'===\s*index\.js\s*===\s*\n([\s\S]+?)(?=\n===|$)', text, re.IGNORECASE)
        css_fallback = re.search(r'===\s*style\.css\s*===\s*\n([\s\S]+?)(?=\n===|$)', text, re.IGNORECASE)
        
        if html_fallback:
            files['index.html'] = html_fallback.group(1).strip()
        if js_fallback:
            files['index.js'] = js_fallback.group(1).strip()
        if css_fallback:
            files['style.css'] = css_fallback.group(1).strip()
    
    # Additional fallback: extract from numbered sections or file headers
    if not (files['index.html'] and files['index.js'] and files['style.css']):
        # Try patterns like "1. index.html:" or "**index.html**"
        patterns = [
            (r'(?:^\d+\.\s*|^##\s*|^\*\*\s*)index\.html(?:\s*:|\*\*:?)\s*\n([\s\S]+?)(?=\n(?:\d+\.|##|\*\*|===)|$)', 'index.html'),
            (r'(?:^\d+\.\s*|^##\s*|^\*\*\s*)index\.js(?:\s*:|\*\*:?)\s*\n([\s\S]+?)(?=\n(?:\d+\.|##|\*\*|===)|$)', 'index.js'),
            (r'(?:^\d+\.\s*|^##\s*|^\*\*\s*)style\.css(?:\s*:|\*\*:?)\s*\n([\s\S]+?)(?=\n(?:\d+\.|##|\*\*|===)|$)', 'style.css')
        ]
        
        for pattern, file_key in patterns:
            if not files[file_key]:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    # Clean up the content by removing any code block markers
                    content = match.group(1).strip()
                    content = re.sub(r'^```\w*\s*\n', '', content)
                    content = re.sub(r'\n```\s*$', '', content)
                    files[file_key] = content.strip()
    
    return files

def format_transformers_js_output(files):
    """Format the three files into a single display string"""
    output = []
    output.append("=== index.html ===")
    output.append(files['index.html'])
    output.append("\n=== index.js ===")
    output.append(files['index.js'])
    output.append("\n=== style.css ===")
    output.append(files['style.css'])
    return '\n'.join(output)

def build_transformers_inline_html(files: dict) -> str:
    """Merge transformers.js three-file output into a single self-contained HTML document.

    - Inlines style.css into a <style> tag
    - Inlines index.js into a <script type="module"> tag
    - Rewrites ESM imports for transformers.js to a stable CDN URL so it works in data: iframes
    """
    import re as _re

    html = files.get('index.html') or ''
    js = files.get('index.js') or ''
    css = files.get('style.css') or ''

    # Normalize JS imports to CDN (handle both @huggingface/transformers and legacy @xenova/transformers)
    cdn_url = "https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.7.3"

    def _normalize_imports(_code: str) -> str:
        if not _code:
            return _code or ""
        _code = _re.sub(r"from\s+['\"]@huggingface/transformers['\"]", f"from '{cdn_url}'", _code)
        _code = _re.sub(r"from\s+['\"]@xenova/transformers['\"]", f"from '{cdn_url}'", _code)
        _code = _re.sub(r"from\s+['\"]https://cdn.jsdelivr.net/npm/@huggingface/transformers@[^'\"]+['\"]", f"from '{cdn_url}'", _code)
        _code = _re.sub(r"from\s+['\"]https://cdn.jsdelivr.net/npm/@xenova/transformers@[^'\"]+['\"]", f"from '{cdn_url}'", _code)
        return _code

    # Extract inline module scripts from index.html, then merge into JS so we control imports
    inline_modules = []
    try:
        for _m in _re.finditer(r"<script\\b[^>]*type=[\"\']module[\"\'][^>]*>([\s\S]*?)</script>", html, flags=_re.IGNORECASE):
            inline_modules.append(_m.group(1))
        if inline_modules:
            html = _re.sub(r"<script\\b[^>]*type=[\"\']module[\"\'][^>]*>[\s\S]*?</script>\\s*", "", html, flags=_re.IGNORECASE)
        # Normalize any external module script URLs that load transformers to a single CDN version (keep the tag)
        html = _re.sub(r"https://cdn\.jsdelivr\.net/npm/@huggingface/transformers@[^'\"<>\s]+", cdn_url, html)
        html = _re.sub(r"https://cdn\.jsdelivr\.net/npm/@xenova/transformers@[^'\"<>\s]+", cdn_url, html)
    except Exception:
        # Best-effort; continue
        pass

    # Merge inline module code with provided index.js, then normalize imports
    combined_js_parts = []
    if inline_modules:
        combined_js_parts.append("\n\n".join(inline_modules))
    if js:
        combined_js_parts.append(js)
    js = "\n\n".join([p for p in combined_js_parts if (p and p.strip())])
    js = _normalize_imports(js)

    # Prepend a small prelude to reduce persistent caching during preview
    # Also ensure a global `transformers` namespace exists for apps relying on it
    # Note: importing env alongside user's own imports is fine in ESM
    if js.strip():
        prelude = (
            f"import {{ env }} from '{cdn_url}';\n"
            "try { env.useBrowserCache = false; } catch (e) {}\n"
            "try { if (env && env.backends && env.backends.onnx && env.backends.onnx.wasm) { env.backends.onnx.wasm.numThreads = 1; env.backends.onnx.wasm.proxy = false; } } catch (e) {}\n"
            f"(async () => {{ try {{ if (typeof globalThis.transformers === 'undefined') {{ const m = await import('{cdn_url}'); globalThis.transformers = m; }} }} catch (e) {{}} }})();\n"
        )
        js = prelude + js

    # If index.html missing or doesn't look like a full document, create a minimal shell
    doc = html.strip()
    if not doc or ('<html' not in doc.lower()):
        doc = (
            "<!DOCTYPE html>\n"
            "<html>\n<head>\n<meta charset=\"UTF-8\">\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n<title>Transformers.js App</title>\n</head>\n"
            "<body>\n<div id=\"app\"></div>\n</body>\n</html>"
        )

    # Remove local references to style.css and index.js to avoid duplicates when inlining
    doc = _re.sub(r"<link[^>]+href=\"[^\"]*style\.css\"[^>]*>\s*", "", doc, flags=_re.IGNORECASE)
    doc = _re.sub(r"<script[^>]+src=\"[^\"]*index\.js\"[^>]*>\s*</script>\s*", "", doc, flags=_re.IGNORECASE)

    # Inline CSS: insert before </head> or create a <head>
    style_tag = f"<style>\n{css}\n</style>" if css else ""
    if style_tag:
        if '</head>' in doc.lower():
            # Preserve original casing by finding closing head case-insensitively
            match = _re.search(r"</head>", doc, flags=_re.IGNORECASE)
            if match:
                idx = match.start()
                doc = doc[:idx] + style_tag + doc[idx:]
        else:
            # No head; insert at top of body
            match = _re.search(r"<body[^>]*>", doc, flags=_re.IGNORECASE)
            if match:
                idx = match.end()
                doc = doc[:idx] + "\n" + style_tag + doc[idx:]
            else:
                # Append at beginning
                doc = style_tag + doc

    # Inline JS: insert before </body>
    script_tag = f"<script type=\"module\">\n{js}\n</script>" if js else ""
    # Lightweight debug console overlay to surface runtime errors inside the iframe
    debug_overlay = (
        "<style>\n"
        "#anycoder-debug{position:fixed;left:0;right:0;bottom:0;max-height:45%;overflow:auto;"
        "background:rgba(0,0,0,.85);color:#9eff9e;padding:.5em;font:12px/1.4 monospace;z-index:2147483647;display:none}"
        "#anycoder-debug pre{margin:0;white-space:pre-wrap;word-break:break-word}"
        "</style>\n"
        "<div id=\"anycoder-debug\"></div>\n"
        "<script>\n"
        "(function(){\n"
        "  const el = document.getElementById('anycoder-debug');\n"
        "  function show(){ if(el && el.style.display!=='block'){ el.style.display='block'; } }\n"
        "  function log(msg){ try{ show(); const pre=document.createElement('pre'); pre.textContent=msg; el.appendChild(pre);}catch(e){} }\n"
        "  const origError = console.error.bind(console);\n"
        "  console.error = function(){ origError.apply(console, arguments); try{ log('console.error: ' + Array.from(arguments).map(a=>{try{return (typeof a==='string')?a:JSON.stringify(a);}catch(e){return String(a);}}).join(' ')); }catch(e){} };\n"
        "  window.addEventListener('error', e => { log('window.onerror: ' + (e && e.message ? e.message : 'Unknown error')); });\n"
        "  window.addEventListener('unhandledrejection', e => { try{ const r=e && e.reason; log('unhandledrejection: ' + (r && (r.message || JSON.stringify(r)))); }catch(err){ log('unhandledrejection'); } });\n"
        "})();\n"
        "</script>"
    )
    # Cleanup script to clear Cache Storage and IndexedDB on unload to free model weights
    cleanup_tag = (
        "<script>\n"
        "(function(){\n"
        "  function cleanup(){\n"
        "    try { if (window.caches && caches.keys) { caches.keys().then(keys => keys.forEach(k => caches.delete(k))); } } catch(e){}\n"
        "    try { if (window.indexedDB && indexedDB.databases) { indexedDB.databases().then(dbs => dbs.forEach(db => db && db.name && indexedDB.deleteDatabase(db.name))); } } catch(e){}\n"
        "  }\n"
        "  window.addEventListener('pagehide', cleanup, { once: true });\n"
        "  window.addEventListener('beforeunload', cleanup, { once: true });\n"
        "})();\n"
        "</script>"
    )
    if script_tag:
        match = _re.search(r"</body>", doc, flags=_re.IGNORECASE)
        if match:
            idx = match.start()
            doc = doc[:idx] + debug_overlay + script_tag + cleanup_tag + doc[idx:]
        else:
            # Append at end
            doc = doc + debug_overlay + script_tag + cleanup_tag

    return doc

def send_transformers_to_sandbox(files: dict) -> str:
    """Build a self-contained HTML document from transformers.js files and return an iframe preview."""
    merged_html = build_transformers_inline_html(files)
    return send_to_sandbox(merged_html)

def parse_multipage_html_output(text: str) -> Dict[str, str]:
    """Parse multi-page HTML output formatted as repeated "=== filename ===" sections.

    Returns a mapping of filename → file content. Supports nested paths like assets/css/styles.css.
    """
    if not text:
        return {}
    # First, strip any markdown fences
    cleaned = remove_code_block(text)
    files: Dict[str, str] = {}
    import re as _re
    pattern = _re.compile(r"^===\s*([^=\n]+?)\s*===\s*\n([\s\S]*?)(?=\n===\s*[^=\n]+?\s*===|\Z)", _re.MULTILINE)
    for m in pattern.finditer(cleaned):
        name = m.group(1).strip()
        content = m.group(2).strip()
        # Remove accidental trailing fences if present
        content = _re.sub(r"^```\w*\s*\n|\n```\s*$", "", content)
        files[name] = content
    return files

def format_multipage_output(files: Dict[str, str]) -> str:
    """Format a dict of files back into === filename === sections.

    Ensures `index.html` appears first if present; others follow sorted by path.
    """
    if not isinstance(files, dict) or not files:
        return ""
    ordered_paths = []
    if 'index.html' in files:
        ordered_paths.append('index.html')
    for path in sorted(files.keys()):
        if path == 'index.html':
            continue
        ordered_paths.append(path)
    parts: list[str] = []
    for path in ordered_paths:
        parts.append(f"=== {path} ===")
        # Avoid trailing extra newlines to keep blocks compact
        parts.append((files.get(path) or '').rstrip())
    return "\n".join(parts)

def validate_and_autofix_files(files: Dict[str, str]) -> Dict[str, str]:
    """Ensure minimal contract for multi-file sites; auto-fix missing pieces.

    Rules:
    - Ensure at least one HTML entrypoint (index.html). If none, synthesize a simple index.html linking discovered pages.
    - For each HTML file, ensure referenced local assets exist in files; if missing, add minimal stubs.
    - Normalize relative paths (strip leading '/').
    """
    if not isinstance(files, dict) or not files:
        return files or {}
    import re as _re

    normalized: Dict[str, str] = {}
    for k, v in files.items():
        safe_key = k.strip().lstrip('/')
        normalized[safe_key] = v

    html_files = [p for p in normalized.keys() if p.lower().endswith('.html')]
    has_index = 'index.html' in normalized

    # If no index.html but some HTML pages exist, create a simple hub index linking to them
    if not has_index and html_files:
        links = '\n'.join([f"<li><a href=\"{p}\">{p}</a></li>" for p in html_files])
        normalized['index.html'] = (
            "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\"/>\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>\n"
            "<title>Site Index</title>\n</head>\n<body>\n<h1>Site</h1>\n<ul>\n"
            + links + "\n</ul>\n</body>\n</html>"
        )

    # Collect references from HTML files
    asset_refs: set[str] = set()
    link_href = _re.compile(r"<link[^>]+href=\"([^\"]+)\"")
    script_src = _re.compile(r"<script[^>]+src=\"([^\"]+)\"")
    img_src = _re.compile(r"<img[^>]+src=\"([^\"]+)\"")
    a_href = _re.compile(r"<a[^>]+href=\"([^\"]+)\"")

    for path, content in list(normalized.items()):
        if not path.lower().endswith('.html'):
            continue
        for patt in (link_href, script_src, img_src, a_href):
            for m in patt.finditer(content or ""):
                ref = (m.group(1) or "").strip()
                if not ref or ref.startswith('http://') or ref.startswith('https://') or ref.startswith('data:') or '#' in ref:
                    continue
                asset_refs.add(ref.lstrip('/'))

    # Add minimal stubs for missing local references (CSS/JS/pages only, not images)
    for ref in list(asset_refs):
        if ref not in normalized:
            if ref.lower().endswith('.css'):
                normalized[ref] = "/* generated stub */\n"
            elif ref.lower().endswith('.js'):
                normalized[ref] = "// generated stub\n"
            elif ref.lower().endswith('.html'):
                normalized[ref] = (
                    "<!DOCTYPE html>\n<html lang=\"en\">\n<head><meta charset=\"utf-8\"/><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/><title>Page</title></head>\n"
                    "<body><main><h1>Placeholder page</h1><p>This page was auto-created to satisfy an internal link.</p></main></body>\n</html>"
                )
            # Note: We no longer create placeholder image files automatically
            # This prevents unwanted SVG stub files from being generated during image generation

    return normalized
def inline_multipage_into_single_preview(files: Dict[str, str]) -> str:
    """Inline local CSS/JS referenced by index.html for preview inside a data: iframe.

    - Uses index.html as the base document
    - Inlines <link href="..."> if the target exists in files
    - Inlines <script src="..."> if the target exists in files
    - Leaves other links (e.g., about.html) untouched; preview covers the home page
    """
    import re as _re
    html = files.get('index.html', '')
    if not html:
        return ""
    doc = html
    # Inline CSS links that point to known files
    def _inline_css(match):
        href = match.group(1)
        if href in files:
            return f"<style>\n{files[href]}\n</style>"
        return match.group(0)
    doc = _re.sub(r"<link[^>]+href=\"([^\"]+)\"[^>]*/?>", _inline_css, doc, flags=_re.IGNORECASE)

    # Inline JS scripts that point to known files
    def _inline_js(match):
        src = match.group(1)
        if src in files:
            return f"<script>\n{files[src]}\n</script>"
        return match.group(0)
    doc = _re.sub(r"<script[^>]+src=\"([^\"]+)\"[^>]*>\s*</script>", _inline_js, doc, flags=_re.IGNORECASE)

    # Inject a lightweight in-iframe client-side navigator to load other HTML files
    try:
        import json as _json
        import base64 as _b64
        import re as _re
        html_pages = {k: v for k, v in files.items() if k.lower().endswith('.html')}
        # Ensure index.html entry restores the current body's HTML
        _m_body = _re.search(r"<body[^>]*>([\s\S]*?)</body>", doc, flags=_re.IGNORECASE)
        _index_body = _m_body.group(1) if _m_body else doc
        html_pages['index.html'] = _index_body
        encoded = _b64.b64encode(_json.dumps(html_pages).encode('utf-8')).decode('ascii')
        nav_script = (
            "<script>\n"  # Simple client-side loader for internal links
            "(function(){\n"
            f"  const MP_FILES = JSON.parse(atob('{encoded}'));\n"
            "  function extractBody(html){\n"
            "    try {\n"
            "      const doc = new DOMParser().parseFromString(html, 'text/html');\n"
            "      const title = doc.querySelector('title'); if (title) document.title = title.textContent || document.title;\n"
            "      return doc.body ? doc.body.innerHTML : html;\n"
            "    } catch(e){ return html; }\n"
            "  }\n"
            "  function loadPage(path){\n"
            "    if (!MP_FILES[path]) return false;\n"
            "    const bodyHTML = extractBody(MP_FILES[path]);\n"
            "    document.body.innerHTML = bodyHTML;\n"
            "    attach();\n"
            "    try { history.replaceState({}, '', '#'+path); } catch(e){}\n"
            "    return true;\n"
            "  }\n"
            "  function clickHandler(e){\n"
            "    const a = e.target && e.target.closest ? e.target.closest('a') : null;\n"
            "    if (!a) return;\n"
            "    const href = a.getAttribute('href') || '';\n"
            "    if (!href || href.startsWith('#') || /^https?:/i.test(href) || href.startsWith('mailto:') || href.startsWith('tel:')) return;\n"
            "    const clean = href.split('#')[0].split('?')[0];\n"
            "    if (MP_FILES[clean]) { e.preventDefault(); loadPage(clean); }\n"
            "  }\n"
            "  function attach(){ document.removeEventListener('click', clickHandler, true); document.addEventListener('click', clickHandler, true); }\n"
            "  document.addEventListener('DOMContentLoaded', function(){ attach(); const initial = (location.hash||'').slice(1); if (initial && MP_FILES[initial]) loadPage(initial); }, { once:true });\n"
            "})();\n"
            "</script>"
        )
        m = _re.search(r"</body>", doc, flags=_re.IGNORECASE)
        if m:
            i = m.start()
            doc = doc[:i] + nav_script + doc[i:]
        else:
            doc = doc + nav_script
    except Exception:
        # Non-fatal in preview
        pass

    return doc

def extract_html_document(text: str) -> str:
    """Return substring starting from the first <!DOCTYPE html> or <html> if present, else original text.

    This ignores prose or planning notes before the actual HTML so previews don't break.
    """
    if not text:
        return text
    lower = text.lower()
    idx = lower.find("<!doctype html")
    if idx == -1:
        idx = lower.find("<html")
    return text[idx:] if idx != -1 else text


def parse_react_output(text):
    """Parse React/Next.js output to extract individual files.

    Supports multi-file sections using === filename === sections.
    """
    if not text:
        return {}

    # Use the generic multipage parser
    try:
        files = parse_multipage_html_output(text) or {}
    except Exception:
        files = {}

    return files if isinstance(files, dict) and files else {}


def history_render(history: History):
    return gr.update(visible=True), history

def clear_history():
    return [], []  # Empty lists for both history and chatbot messages

def create_multimodal_message(text, image=None):
    """Create a chat message. For broad provider compatibility, always return content as a string.

    Some providers (e.g., Hugging Face router endpoints like Cerebras) expect `content` to be a string,
    not a list of typed parts. To avoid 422 validation errors, we inline a brief note when an image is provided.
    """
    if image is None:
        return {"role": "user", "content": text}
    # Keep providers happy: avoid structured multimodal payloads; add a short note instead
    # If needed, this can be enhanced per-model with proper multimodal schemas.
    return {"role": "user", "content": f"{text}\n\n[An image was provided as reference.]"}
def apply_search_replace_changes(original_content: str, changes_text: str) -> str:
    """Apply search/replace changes to content (HTML, Python, etc.)"""
    if not changes_text.strip():
        return original_content
    
    # If the model didn't use the block markers, try a CSS-rule fallback where
    # provided blocks like `.selector { ... }` replace matching CSS rules.
    if (SEARCH_START not in changes_text) and (DIVIDER not in changes_text) and (REPLACE_END not in changes_text):
        try:
            import re  # Local import to avoid global side effects
            updated_content = original_content
            replaced_any_rule = False
            # Find CSS-like rule blocks in the changes_text
            # This is a conservative matcher that looks for `selector { ... }`
            css_blocks = re.findall(r"([^{]+)\{([\s\S]*?)\}", changes_text, flags=re.MULTILINE)
            for selector_raw, body_raw in css_blocks:
                selector = selector_raw.strip()
                body = body_raw.strip()
                if not selector:
                    continue
                # Build a regex to find the existing rule for this selector
                # Capture opening `{` and closing `}` to preserve them; replace inner body.
                pattern = re.compile(rf"({re.escape(selector)}\s*\{{)([\s\S]*?)(\}})")
                def _replace_rule(match):
                    nonlocal replaced_any_rule
                    replaced_any_rule = True
                    prefix, existing_body, suffix = match.groups()
                    # Preserve indentation of the existing first body line if present
                    first_line_indent = ""
                    for line in existing_body.splitlines():
                        stripped = line.lstrip(" \t")
                        if stripped:
                            first_line_indent = line[: len(line) - len(stripped)]
                            break
                    # Re-indent provided body with the detected indent
                    if body:
                        new_body_lines = [first_line_indent + line if line.strip() else line for line in body.splitlines()]
                        new_body_text = "\n" + "\n".join(new_body_lines) + "\n"
                    else:
                        new_body_text = existing_body  # If empty body provided, keep existing
                    return f"{prefix}{new_body_text}{suffix}"
                updated_content, num_subs = pattern.subn(_replace_rule, updated_content, count=1)
            if replaced_any_rule:
                return updated_content
        except Exception:
            # Fallback silently to the standard block-based application
            pass

    # Split the changes text into individual search/replace blocks
    blocks = []
    current_block = ""
    lines = changes_text.split('\n')
    
    for line in lines:
        if line.strip() == SEARCH_START:
            if current_block.strip():
                blocks.append(current_block.strip())
            current_block = line + '\n'
        elif line.strip() == REPLACE_END:
            current_block += line + '\n'
            blocks.append(current_block.strip())
            current_block = ""
        else:
            current_block += line + '\n'
    
    if current_block.strip():
        blocks.append(current_block.strip())
    
    modified_content = original_content
    
    for block in blocks:
        if not block.strip():
            continue
            
        # Parse the search/replace block
        lines = block.split('\n')
        search_lines = []
        replace_lines = []
        in_search = False
        in_replace = False
        
        for line in lines:
            if line.strip() == SEARCH_START:
                in_search = True
                in_replace = False
            elif line.strip() == DIVIDER:
                in_search = False
                in_replace = True
            elif line.strip() == REPLACE_END:
                in_replace = False
            elif in_search:
                search_lines.append(line)
            elif in_replace:
                replace_lines.append(line)
        
        # Apply the search/replace
        if search_lines:
            search_text = '\n'.join(search_lines).strip()
            replace_text = '\n'.join(replace_lines).strip()
            
            if search_text in modified_content:
                modified_content = modified_content.replace(search_text, replace_text)
            else:
                # If exact block match fails, attempt a CSS-rule fallback using the replace_text
                try:
                    import re
                    updated_content = modified_content
                    replaced_any_rule = False
                    css_blocks = re.findall(r"([^{]+)\{([\s\S]*?)\}", replace_text, flags=re.MULTILINE)
                    for selector_raw, body_raw in css_blocks:
                        selector = selector_raw.strip()
                        body = body_raw.strip()
                        if not selector:
                            continue
                        pattern = re.compile(rf"({re.escape(selector)}\s*\{{)([\s\S]*?)(\}})")
                        def _replace_rule(match):
                            nonlocal replaced_any_rule
                            replaced_any_rule = True
                            prefix, existing_body, suffix = match.groups()
                            first_line_indent = ""
                            for line in existing_body.splitlines():
                                stripped = line.lstrip(" \t")
                                if stripped:
                                    first_line_indent = line[: len(line) - len(stripped)]
                                    break
                            if body:
                                new_body_lines = [first_line_indent + line if line.strip() else line for line in body.splitlines()]
                                new_body_text = "\n" + "\n".join(new_body_lines) + "\n"
                            else:
                                new_body_text = existing_body
                            return f"{prefix}{new_body_text}{suffix}"
                        updated_content, num_subs = pattern.subn(_replace_rule, updated_content, count=1)
                    if replaced_any_rule:
                        modified_content = updated_content
                    else:
                        print(f"Warning: Search text not found in content: {search_text[:100]}...")
                except Exception:
                    print(f"Warning: Search text not found in content: {search_text[:100]}...")
    
    return modified_content

def apply_transformers_js_search_replace_changes(original_formatted_content: str, changes_text: str) -> str:
    """Apply search/replace changes to transformers.js formatted content (three files)"""
    if not changes_text.strip():
        return original_formatted_content
    
    # Parse the original formatted content to get the three files
    files = parse_transformers_js_output(original_formatted_content)
    
    # Split the changes text into individual search/replace blocks
    blocks = []
    current_block = ""
    lines = changes_text.split('\n')
    
    for line in lines:
        if line.strip() == SEARCH_START:
            if current_block.strip():
                blocks.append(current_block.strip())
            current_block = line + '\n'
        elif line.strip() == REPLACE_END:
            current_block += line + '\n'
            blocks.append(current_block.strip())
            current_block = ""
        else:
            current_block += line + '\n'
    
    if current_block.strip():
        blocks.append(current_block.strip())
    
    # Process each block and apply changes to the appropriate file
    for block in blocks:
        if not block.strip():
            continue
            
        # Parse the search/replace block
        lines = block.split('\n')
        search_lines = []
        replace_lines = []
        in_search = False
        in_replace = False
        target_file = None
        
        for line in lines:
            if line.strip() == SEARCH_START:
                in_search = True
                in_replace = False
            elif line.strip() == DIVIDER:
                in_search = False
                in_replace = True
            elif line.strip() == REPLACE_END:
                in_replace = False
            elif in_search:
                search_lines.append(line)
            elif in_replace:
                replace_lines.append(line)
        
        # Determine which file this change targets based on the search content
        if search_lines:
            search_text = '\n'.join(search_lines).strip()
            replace_text = '\n'.join(replace_lines).strip()
            
            # Check which file contains the search text
            if search_text in files['index.html']:
                target_file = 'index.html'
            elif search_text in files['index.js']:
                target_file = 'index.js'
            elif search_text in files['style.css']:
                target_file = 'style.css'
            
            # Apply the change to the target file
            if target_file and search_text in files[target_file]:
                files[target_file] = files[target_file].replace(search_text, replace_text)
            else:
                print(f"Warning: Search text not found in any transformers.js file: {search_text[:100]}...")
    
    # Reformat the modified files
    return format_transformers_js_output(files)

def send_to_sandbox(code):
    """Render HTML in a sandboxed iframe. Assumes full HTML is provided by prompts."""
    html_doc = (code or "").strip()
    # For preview only: inline local file URLs as data URIs so the
    # data: iframe can load them. The original code (shown to the user) still contains file URLs.
    try:
        import re
        import base64 as _b64
        import mimetypes as _mtypes
        import urllib.parse as _uparse
        def _file_url_to_data_uri(file_url: str) -> str | None:
            try:
                parsed = _uparse.urlparse(file_url)
                path = _uparse.unquote(parsed.path)
                if not path:
                    return None
                with open(path, 'rb') as _f:
                    raw = _f.read()
                mime = _mtypes.guess_type(path)[0] or 'application/octet-stream'
                
                b64 = _b64.b64encode(raw).decode()
                return f"data:{mime};base64,{b64}"
            except Exception as e:
                print(f"[Sandbox] Failed to convert file URL to data URI: {str(e)}")
                return None
        def _repl_double(m):
            url = m.group(1)
            data_uri = _file_url_to_data_uri(url)
            return f'src="{data_uri}"' if data_uri else m.group(0)
        def _repl_single(m):
            url = m.group(1)
            data_uri = _file_url_to_data_uri(url)
            return f"src='{data_uri}'" if data_uri else m.group(0)
        html_doc = re.sub(r'src="(file:[^"]+)"', _repl_double, html_doc)
        html_doc = re.sub(r"src='(file:[^']+)'", _repl_single, html_doc)
                
    except Exception:
        # Best-effort; continue without inlining
        pass
    encoded_html = base64.b64encode(html_doc.encode('utf-8')).decode('utf-8')
    data_uri = f"data:text/html;charset=utf-8;base64,{encoded_html}"
    iframe = f'<iframe src="{data_uri}" width="100%" height="920px" sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals allow-presentation" allow="display-capture"></iframe>'
    return iframe

def is_streamlit_code(code: str) -> bool:
    """Heuristic check to determine if Python code is a Streamlit app."""
    if not code:
        return False
    lowered = code.lower()
    return ("import streamlit" in lowered) or ("from streamlit" in lowered) or ("st." in code and "streamlit" in lowered)

def clean_requirements_txt_content(content: str) -> str:
    """
    Clean up requirements.txt content to remove markdown formatting.
    This function removes code blocks, markdown lists, headers, and other formatting
    that might be mistakenly included by LLMs.
    """
    if not content:
        return content
    
    # First, remove code blocks if present
    if '```' in content:
        content = remove_code_block(content)
    
    # Process line by line to remove markdown formatting
    lines = content.split('\n')
    clean_lines = []
    
    for line in lines:
        stripped_line = line.strip()
        
        # Skip empty lines
        if not stripped_line:
            continue
        
        # Skip lines that are markdown formatting
        if (stripped_line == '```' or 
            stripped_line.startswith('```') or
            # Skip markdown headers (## Header) but keep comments (# comment)
            (stripped_line.startswith('#') and len(stripped_line) > 1 and stripped_line[1] != ' ') or
            stripped_line.startswith('**') or  # Skip bold text
            stripped_line.startswith('===') or  # Skip section dividers
            stripped_line.startswith('---') or  # Skip horizontal rules
            # Skip common explanatory text patterns
            stripped_line.lower().startswith('here') or
            stripped_line.lower().startswith('this') or
            stripped_line.lower().startswith('the ') or
            stripped_line.lower().startswith('based on') or
            stripped_line.lower().startswith('dependencies') or
            stripped_line.lower().startswith('requirements')):
            continue
        
        # Handle markdown list items (- item or * item)
        if (stripped_line.startswith('- ') or stripped_line.startswith('* ')):
            # Extract the package name after the list marker
            stripped_line = stripped_line[2:].strip()
            if not stripped_line:
                continue
        
        # Keep lines that look like valid package specifications
        # Valid lines: package names, git+https://, comments starting with "# "
        if (stripped_line.startswith('# ') or  # Valid comments
            stripped_line.startswith('git+') or  # Git dependencies
            stripped_line[0].isalnum() or  # Package names start with alphanumeric
            '==' in stripped_line or  # Version specifications
            '>=' in stripped_line or  # Version specifications
            '<=' in stripped_line or  # Version specifications
            '~=' in stripped_line):  # Version specifications
            clean_lines.append(stripped_line)
    
    result = '\n'.join(clean_lines)
    
    # Ensure it ends with a newline
    if result and not result.endswith('\n'):
        result += '\n'
    
    return result if result else "# No additional dependencies required\n"

def parse_multi_file_python_output(code: str) -> dict:
    """Parse multi-file Python output (Gradio/Streamlit) into separate files"""
    files = {}
    if not code:
        return files
    
    # Look for file separators like === filename.py ===
    import re
    file_pattern = r'=== ([^=]+) ==='
    parts = re.split(file_pattern, code)
    
    if len(parts) > 1:
        # Multi-file format detected
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                filename = parts[i].strip()
                content = parts[i + 1].strip()
                
                # Clean up requirements.txt to remove markdown formatting
                if filename == 'requirements.txt':
                    content = clean_requirements_txt_content(content)
                
                files[filename] = content
    else:
        # Single file - check if it's a space import or regular code
        if "IMPORTED PROJECT FROM HUGGING FACE SPACE" in code:
            # This is already a multi-file import, try to parse it
            lines = code.split('\n')
            current_file = None
            current_content = []
            
            for line in lines:
                if line.startswith('=== ') and line.endswith(' ==='):
                    # Save previous file
                    if current_file and current_content:
                        content = '\n'.join(current_content)
                        # Clean up requirements.txt to remove markdown formatting
                        if current_file == 'requirements.txt':
                            content = clean_requirements_txt_content(content)
                        files[current_file] = content
                    # Start new file
                    current_file = line[4:-4].strip()
                    current_content = []
                elif current_file:
                    current_content.append(line)
            
            # Save last file
            if current_file and current_content:
                content = '\n'.join(current_content)
                # Clean up requirements.txt to remove markdown formatting
                if current_file == 'requirements.txt':
                    content = clean_requirements_txt_content(content)
                files[current_file] = content
        else:
            # Single file code - determine appropriate filename
            if is_streamlit_code(code):
                files['streamlit_app.py'] = code
            elif 'import gradio' in code.lower() or 'from gradio' in code.lower():
                files['app.py'] = code
            else:
                files['app.py'] = code
    
    return files

def format_multi_file_python_output(files: dict) -> str:
    """Format multiple Python files into the standard multi-file format"""
    if not files:
        return ""
    
    if len(files) == 1:
        # Single file - return as is
        return list(files.values())[0]
    
    # Multi-file format
    output = []
    
    # Order files: main app first, then utils, models, config, requirements
    file_order = ['app.py', 'streamlit_app.py', 'main.py', 'utils.py', 'models.py', 'config.py', 'requirements.txt']
    ordered_files = []
    
    # Add files in preferred order
    for preferred_file in file_order:
        if preferred_file in files:
            ordered_files.append(preferred_file)
    
    # Add remaining files
    for filename in sorted(files.keys()):
        if filename not in ordered_files:
            ordered_files.append(filename)
    
    # Format output
    for filename in ordered_files:
        output.append(f"=== {filename} ===")
        
        # Clean up requirements.txt content if it's being formatted
        content = files[filename]
        if filename == 'requirements.txt':
            content = clean_requirements_txt_content(content)
        
        output.append(content)
        output.append("")  # Empty line between files
    
    return '\n'.join(output)

def send_streamlit_to_stlite(code: str) -> str:
    """Render Streamlit code using stlite inside a sandboxed iframe for preview."""
    # Build an HTML document that loads stlite and mounts the Streamlit app defined inline
    html_doc = (
        """<!doctype html>
<html>
  <head>
    <meta charset=\"UTF-8\" />
    <meta http-equiv=\"X-UA-Compatible\" content=\"IE=edge\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1, shrink-to-fit=no\" />
    <title>Streamlit Preview</title>
    <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/@stlite/browser@0.86.0/build/stlite.css\" />
    <style>html,body{margin:0;padding:0;height:100%;} streamlit-app{display:block;height:100%;}</style>
    <script type=\"module\" src=\"https://cdn.jsdelivr.net/npm/@stlite/browser@0.86.0/build/stlite.js\"></script>
  </head>
  <body>
    <streamlit-app>
"""
        + (code or "")
        + """
    </streamlit-app>
  </body>
</html>
"""
    )
    encoded_html = base64.b64encode(html_doc.encode('utf-8')).decode('utf-8')
    data_uri = f"data:text/html;charset=utf-8;base64,{encoded_html}"
    iframe = f'<iframe src="{data_uri}" width="100%" height="920px" sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals allow-presentation" allow="display-capture"></iframe>'
    return iframe

def is_gradio_code(code: str) -> bool:
    """Heuristic check to determine if Python code is a Gradio app."""
    if not code:
        return False
    lowered = code.lower()
    return (
        "import gradio" in lowered
        or "from gradio" in lowered
        or "gr.Interface(" in code
        or "gr.Blocks(" in code
    )

def send_gradio_to_lite(code: str) -> str:
    """Render Gradio code using gradio-lite inside a sandboxed iframe for preview."""
    html_doc = (
        """<!doctype html>
<html>
  <head>
    <meta charset=\"UTF-8\" />
    <meta http-equiv=\"X-UA-Compatible\" content=\"IE=edge\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1, shrink-to-fit=no\" />
    <title>Gradio Preview</title>
    <script type=\"module\" crossorigin src=\"https://cdn.jsdelivr.net/npm/@gradio/lite/dist/lite.js\"></script>
    <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/@gradio/lite/dist/lite.css\" />
    <style>html,body{margin:0;padding:0;height:100%;} gradio-lite{display:block;height:100%;}</style>
  </head>
  <body>
    <gradio-lite>
"""
        + (code or "")
        + """
    </gradio-lite>
  </body>
</html>
"""
    )
    encoded_html = base64.b64encode(html_doc.encode('utf-8')).decode('utf-8')
    data_uri = f"data:text/html;charset=utf-8;base64,{encoded_html}"
    iframe = f'<iframe src="{data_uri}" width="100%" height="920px" sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals allow-presentation" allow="display-capture"></iframe>'
    return iframe

stop_generation = False


def check_authentication(profile: gr.OAuthProfile | None = None, token: gr.OAuthToken | None = None) -> tuple[bool, str]:
    """Check if user is authenticated and return status with message."""
    if not profile or not token:
        return False, "Please log in with your Hugging Face account to use AnyCoder."
    
    if not token.token:
        return False, "Authentication token is invalid. Please log in again."
    
    return True, f"Authenticated as {profile.username}"


def update_ui_for_auth_status(profile: gr.OAuthProfile | None = None, token: gr.OAuthToken | None = None):
    """Update UI components based on authentication status."""
    is_authenticated, auth_message = check_authentication(profile, token)
    
    if is_authenticated:
        # User is authenticated - enable all components
        return {
            # Enable main input and button
            input: gr.update(interactive=True, placeholder="Describe your application..."),
            btn: gr.update(interactive=True, variant="primary")
        }
    else:
        # User not authenticated - disable main components
        return {
            # Disable main input and button with clear messaging
            input: gr.update(
                interactive=False, 
                placeholder="🔒 Click Sign in with Hugging Face button to use AnyCoder for free"
            ),
            btn: gr.update(interactive=False, variant="secondary")
        }


def generation_code(query: str | None, vlm_image: Optional[gr.Image], _setting: Dict[str, str], _history: Optional[History], _current_model: Dict, language: str = "html", provider: str = "auto", profile: gr.OAuthProfile | None = None, token: gr.OAuthToken | None = None):
    # Check authentication first
    is_authenticated, auth_message = check_authentication(profile, token)
    if not is_authenticated:
        error_message = f"🔒 Authentication Required\n\n{auth_message}\n\nPlease click the 'Sign in with Hugging Face' button in the sidebar to continue."
        yield {
            code_output: error_message,
            history_output: history_to_chatbot_messages(_history or []),
        }
        return
    
    if query is None:
        query = ''
    if _history is None:
        _history = []
    # Ensure _history is always a list of lists with at least 2 elements per item
    if not isinstance(_history, list):
        _history = []
    _history = [h for h in _history if isinstance(h, list) and len(h) == 2]

    # Check if there's existing content in history to determine if this is a modification request
    has_existing_content = False
    last_assistant_msg = ""
    if _history and len(_history[-1]) > 1:
        last_assistant_msg = _history[-1][1]
        # Check for various content types that indicate an existing project
        if ('<!DOCTYPE html>' in last_assistant_msg or 
            '<html' in last_assistant_msg or
            'import gradio' in last_assistant_msg or
            'import streamlit' in last_assistant_msg or
            'def ' in last_assistant_msg and 'app' in last_assistant_msg or
            'IMPORTED PROJECT FROM HUGGING FACE SPACE' in last_assistant_msg or
            '=== index.html ===' in last_assistant_msg or
            '=== index.js ===' in last_assistant_msg or
            '=== style.css ===' in last_assistant_msg or
            '=== app.py ===' in last_assistant_msg or
            '=== requirements.txt ===' in last_assistant_msg):
            has_existing_content = True

    # If this is a modification request, try to apply search/replace first
    if has_existing_content and query.strip():
        try:
            # Use the current model to generate search/replace instructions
            client = get_inference_client(_current_model['id'], provider)
            
            system_prompt = """You are a code editor assistant. Given existing code and modification instructions, generate EXACT search/replace blocks.

CRITICAL REQUIREMENTS:
1. Use EXACTLY these markers: <<<<<<< SEARCH, =======, >>>>>>> REPLACE
2. The SEARCH block must match the existing code EXACTLY (including whitespace, indentation, line breaks)
3. The REPLACE block should contain the modified version
4. Only include the specific lines that need to change, with enough context to make them unique
5. Generate multiple search/replace blocks if needed for different changes
6. Do NOT include any explanations or comments outside the blocks

Example format:
<<<<<<< SEARCH
    function oldFunction() {
        return "old";
    }
=======
    function newFunction() {
        return "new";
    }
>>>>>>> REPLACE"""

            user_prompt = f"""Existing code:
{last_assistant_msg}
Modification instructions:
{query}

Generate the exact search/replace blocks needed to make these changes."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Generate search/replace instructions
            if _current_model.get('type') == 'openai':
                response = client.chat.completions.create(
                    model=get_real_model_id(_current_model['id']),
                    messages=messages,
                    max_tokens=4000,
                    temperature=0.1
                )
                changes_text = response.choices[0].message.content
            elif _current_model.get('type') == 'mistral':
                response = client.chat.complete(
                    model=get_real_model_id(_current_model['id']),
                    messages=messages,
                    max_tokens=4000,
                    temperature=0.1
                )
                changes_text = response.choices[0].message.content
            else:  # Hugging Face or other
                completion = client.chat.completions.create(
                    model=get_real_model_id(_current_model['id']),
                    messages=messages,
                    max_tokens=4000,
                    temperature=0.1
                )
                changes_text = completion.choices[0].message.content
            
            # Apply the search/replace changes
            if language == "transformers.js" and ('=== index.html ===' in last_assistant_msg):
                modified_content = apply_transformers_js_search_replace_changes(last_assistant_msg, changes_text)
            else:
                modified_content = apply_search_replace_changes(last_assistant_msg, changes_text)
            
            # If changes were successfully applied, return the modified content
            if modified_content != last_assistant_msg:
                _history.append([query, modified_content])
                
                # Generate deployment message instead of preview
                deploy_message = f"""
                <div style='padding: 1.5em; text-align: center; background: #f0f9ff; border: 2px solid #0ea5e9; border-radius: 10px; color: #0c4a6e;'>
                    <h3 style='margin-top: 0; color: #0ea5e9;'>✅ Code Updated Successfully!</h3>
                    <p style='margin: 0.5em 0; font-size: 1.1em;'>Your {language.upper()} code has been modified and is ready for deployment.</p>
                    <p style='margin: 0.5em 0; font-weight: bold;'>👉 Use the Deploy button in the sidebar to publish your app!</p>
                </div>
                """
                
                yield {
                    code_output: modified_content,
                    history: _history,
                    history_output: history_to_chatbot_messages(_history),
                }
                return
                
        except Exception as e:
            print(f"Search/replace failed, falling back to normal generation: {e}")
            # If search/replace fails, continue with normal generation

    # Create/lookup a session id for temp-file tracking and cleanup
    if _setting is not None and isinstance(_setting, dict):
        session_id = _setting.get("__session_id__")
        if not session_id:
            session_id = str(uuid.uuid4())
            _setting["__session_id__"] = session_id
    else:
        session_id = str(uuid.uuid4())

    # Update Gradio system prompts if needed
    if language == "gradio":
        update_gradio_system_prompts()

    # Choose system prompt based on context
    # Special case: If user is asking about model identity, use neutral prompt
    if query and any(phrase in query.lower() for phrase in ["what model are you", "who are you", "identify yourself", "what ai are you", "which model"]):
        system_prompt = "You are a helpful AI assistant. Please respond truthfully about your identity and capabilities."
    elif has_existing_content:
        # Use follow-up prompt for modifying existing content
        if language == "transformers.js":
            system_prompt = TransformersJSFollowUpSystemPrompt
        elif language == "gradio":
            system_prompt = GradioFollowUpSystemPrompt
        elif language == "react":
            system_prompt = REACT_FOLLOW_UP_SYSTEM_PROMPT
        else:
            system_prompt = FollowUpSystemPrompt
    else:
        # Use language-specific prompt
        if language == "html":
            # Dynamic file selection always enabled
            system_prompt = DYNAMIC_MULTIPAGE_HTML_SYSTEM_PROMPT
        elif language == "transformers.js":
            system_prompt = TRANSFORMERS_JS_SYSTEM_PROMPT
        elif language == "react":
            system_prompt = REACT_SYSTEM_PROMPT
        elif language == "gradio":
            system_prompt = GRADIO_SYSTEM_PROMPT
        elif language == "streamlit":
            system_prompt = STREAMLIT_SYSTEM_PROMPT
        elif language == "json":
            system_prompt = JSON_SYSTEM_PROMPT
        elif language == "comfyui":
            system_prompt = get_comfyui_system_prompt()
        else:
            system_prompt = GENERIC_SYSTEM_PROMPT.format(language=language)

    messages = history_to_messages(_history, system_prompt)



    # Use the original query without search enhancement
    enhanced_query = query

    # Check if this is GLM-4.5 model and handle with simple HuggingFace InferenceClient
    if _current_model["id"] == "zai-org/GLM-4.5":
        if vlm_image is not None:
            messages.append(create_multimodal_message(enhanced_query, vlm_image))
        else:
            messages.append({'role': 'user', 'content': enhanced_query})
        
        try:
            client = InferenceClient(
                provider="auto",
                api_key=os.environ["HF_TOKEN"],
                bill_to="huggingface",
            )
            
            stream = client.chat.completions.create(
                model="zai-org/GLM-4.5",
                messages=messages,
                stream=True,
                max_tokens=16384,
            )
            
            content = ""
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content += chunk.choices[0].delta.content
                    clean_code = remove_code_block(content)
                    # Show generation progress message
                    progress_message = f"""
                    <div style='padding: 1.5em; text-align: center; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; border-radius: 10px;'>
                        <h3 style='margin-top: 0; color: white;'>⚡ Generating Your {language.upper()} App...</h3>
                        <p style='margin: 0.5em 0; opacity: 0.9;'>Code is being generated in real-time!</p>
                        <div style='background: rgba(255,255,255,0.2); padding: 1em; border-radius: 8px; margin: 1em 0;'>
                            <p style='margin: 0; font-size: 1.1em;'>Get ready to deploy once generation completes!</p>
                        </div>
                    </div>
                    """
                    yield {
                        code_output: gr.update(value=clean_code, language=get_gradio_language(language)),
                        history_output: history_to_chatbot_messages(_history),
                    }
            
        except Exception as e:
            content = f"Error with GLM-4.5: {str(e)}\n\nPlease make sure HF_TOKEN environment variable is set."
        
        clean_code = remove_code_block(content)
        
        # Use clean code as final content without media generation
        final_content = clean_code
        
        _history.append([query, final_content])
        
        if language == "transformers.js":
            files = parse_transformers_js_output(clean_code)
            if files['index.html'] and files['index.js'] and files['style.css']:
                formatted_output = format_transformers_js_output(files)
                yield {
                    code_output: formatted_output,
                    history: _history,
                    history_output: history_to_chatbot_messages(_history),
                }
            else:
                yield {
                    code_output: clean_code,
                    history: _history,
                    history_output: history_to_chatbot_messages(_history),
                }
        else:
            if has_existing_content and not (clean_code.strip().startswith("<!DOCTYPE html>") or clean_code.strip().startswith("<html")):
                last_content = _history[-1][1] if _history and len(_history[-1]) > 1 else ""
                modified_content = apply_search_replace_changes(last_content, clean_code)
                clean_content = remove_code_block(modified_content)
                
                # Use clean content without media generation
                
                yield {
                    code_output: clean_content,
                    history: _history,
                    history_output: history_to_chatbot_messages(_history),
                }
            else:
                # Use clean code as final content without media generation
                final_content = clean_code
                
                # Generate deployment message instead of preview
                deploy_message = f"""
                <div style='padding: 2em; text-align: center; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; border-radius: 12px; box-shadow: 0 4px 20px rgba(16, 185, 129, 0.3);'>
                    <h2 style='margin-top: 0; font-size: 2em;'>🎉 Code Generated Successfully!</h2>
                    <p style='font-size: 1.2em; margin: 1em 0; opacity: 0.95;'>Your {language.upper()} application is ready to deploy!</p>
                    
                    <div style='background: rgba(255,255,255,0.15); padding: 1.5em; border-radius: 10px; margin: 1.5em 0;'>
                        <h3 style='margin-top: 0; font-size: 1.3em;'>🚀 Next Steps:</h3>
                        <div style='text-align: left; max-width: 500px; margin: 0 auto;'>
                            <p style='margin: 0.8em 0; font-size: 1.1em; display: flex; align-items: center;'>
                                <span style='background: rgba(255,255,255,0.2); border-radius: 50%; width: 24px; height: 24px; display: inline-flex; align-items: center; justify-content: center; margin-right: 10px; font-weight: bold;'>1</span>
                                Use the <strong>Deploy button</strong> in the sidebar
                            </p>
                            <p style='margin: 0.8em 0; font-size: 1.1em; display: flex; align-items: center;'>
                                <span style='background: rgba(255,255,255,0.2); border-radius: 50%; width: 24px; height: 24px; display: inline-flex; align-items: center; justify-content: center; margin-right: 10px; font-weight: bold;'>2</span>
                                Enter your app name below
                            </p>
                            <p style='margin: 0.8em 0; font-size: 1.1em; display: flex; align-items: center;'>
                                <span style='background: rgba(255,255,255,0.2); border-radius: 50%; width: 24px; height: 24px; display: inline-flex; align-items: center; justify-content: center; margin-right: 10px; font-weight: bold;'>3</span>
                                Click <strong>"Publish"</strong>
                            </p>
                            <p style='margin: 0.8em 0; font-size: 1.1em; display: flex; align-items: center;'>
                                <span style='background: rgba(255,255,255,0.2); border-radius: 50%; width: 24px; height: 24px; display: inline-flex; align-items: center; justify-content: center; margin-right: 10px; font-weight: bold;'>4</span>
                                Share your creation! 🌍
                            </p>
                        </div>
                    </div>
                    
                    <p style='font-size: 1em; opacity: 0.9; margin-bottom: 0;'>
                        💡 Your app will be live on Hugging Face Spaces in seconds!
                    </p>
                </div>
                """
                
                yield {
                    code_output: final_content,
                    history: _history,
                    history_output: history_to_chatbot_messages(_history),
                }
        return
    
    # Handle GLM-4.5V (multimodal vision)
    if _current_model["id"] == "zai-org/GLM-4.5V":
        # Build structured messages with a strong system prompt to enforce full HTML output
        structured = [
            {"role": "system", "content": GLM45V_HTML_SYSTEM_PROMPT}
        ]
        if vlm_image is not None:
            user_msg = {
                "role": "user",
                "content": [
                    {"type": "text", "text": enhanced_query},
                ],
            }
            try:
                import io, base64
                from PIL import Image
                import numpy as np
                if isinstance(vlm_image, np.ndarray):
                    vlm_image = Image.fromarray(vlm_image)
                buf = io.BytesIO()
                vlm_image.save(buf, format="PNG")
                b64 = base64.b64encode(buf.getvalue()).decode()
                user_msg["content"].append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"}
                })
                structured.append(user_msg)
            except Exception:
                structured.append({"role": "user", "content": enhanced_query})
        else:
            structured.append({"role": "user", "content": enhanced_query})

        try:
            client = InferenceClient(
                provider="auto",
                api_key=os.environ["HF_TOKEN"],
                bill_to="huggingface",
            )
            stream = client.chat.completions.create(
                model="zai-org/GLM-4.5V",
                messages=structured,
                stream=True,
            )
            content = ""
            for chunk in stream:
                if getattr(chunk, "choices", None) and chunk.choices and getattr(chunk.choices[0], "delta", None) and getattr(chunk.choices[0].delta, "content", None):
                    content += chunk.choices[0].delta.content
                    clean_code = remove_code_block(content)
                    # Ensure escaped newlines/tabs from model are rendered correctly
                    if "\\n" in clean_code:
                        clean_code = clean_code.replace("\\n", "\n")
                    if "\\t" in clean_code:
                        clean_code = clean_code.replace("\\t", "\t")
                    preview_val = None
                    if language == "html":
                        _mpc = parse_multipage_html_output(clean_code)
                        _mpc = validate_and_autofix_files(_mpc)
                        preview_val = send_to_sandbox(inline_multipage_into_single_preview(_mpc)) if _mpc.get('index.html') else send_to_sandbox(clean_code)
                    elif language == "python" and is_streamlit_code(clean_code):
                        preview_val = send_streamlit_to_stlite(clean_code)
                    yield {
                        code_output: gr.update(value=clean_code, language=get_gradio_language(language)),
                        history_output: history_to_chatbot_messages(_history),
                    }
        except Exception as e:
            content = f"Error with GLM-4.5V: {str(e)}\n\nPlease make sure HF_TOKEN environment variable is set."

        clean_code = remove_code_block(content)
        if "\\n" in clean_code:
            clean_code = clean_code.replace("\\n", "\n")
        if "\\t" in clean_code:
            clean_code = clean_code.replace("\\t", "\t")
        _history.append([query, clean_code])
        preview_val = None
        if language == "html":
            _mpc2 = parse_multipage_html_output(clean_code)
            _mpc2 = validate_and_autofix_files(_mpc2)
            preview_val = send_to_sandbox(inline_multipage_into_single_preview(_mpc2)) if _mpc2.get('index.html') else send_to_sandbox(clean_code)
        elif language == "python" and is_streamlit_code(clean_code):
            preview_val = send_streamlit_to_stlite(clean_code)
        yield {
            code_output: clean_code,
            history: _history,
            history_output: history_to_chatbot_messages(_history),
        }
        return

    # Use dynamic client based on selected model (for non-GLM-4.5 models)
    client = get_inference_client(_current_model["id"], provider)

    if vlm_image is not None:
        messages.append(create_multimodal_message(enhanced_query, vlm_image))
    else:
        messages.append({'role': 'user', 'content': enhanced_query})
    try:
        # Handle Mistral API method difference
        if _current_model["id"] in ("codestral-2508", "mistral-medium-2508"):
            completion = client.chat.stream(
                model=get_real_model_id(_current_model["id"]),
                messages=messages,
                max_tokens=16384
            )

        else:
            # Poe expects model id "GPT-5" and uses max_tokens
            if _current_model["id"] == "gpt-5":
                completion = client.chat.completions.create(
                    model="GPT-5",
                    messages=messages,
                    stream=True,
                    max_tokens=16384
                )
            elif _current_model["id"] == "grok-4":
                completion = client.chat.completions.create(
                    model="Grok-4",
                    messages=messages,
                    stream=True,
                    max_tokens=16384
                )
            elif _current_model["id"] == "claude-opus-4.1":
                completion = client.chat.completions.create(
                    model="Claude-Opus-4.1",
                    messages=messages,
                    stream=True,
                    max_tokens=16384
                )
            elif _current_model["id"] == "claude-sonnet-4.5":
                completion = client.chat.completions.create(
                    model="Claude-Sonnet-4.5",
                    messages=messages,
                    stream=True,
                    max_tokens=16384
                )
            elif _current_model["id"] == "claude-haiku-4.5":
                completion = client.chat.completions.create(
                    model="Claude-Haiku-4.5",
                    messages=messages,
                    stream=True,
                    max_tokens=16384
                )
            else:
                completion = client.chat.completions.create(
                    model=get_real_model_id(_current_model["id"]),
                    messages=messages,
                    stream=True,
                    max_tokens=16384
                )
        content = ""
        # For Poe/GPT-5, maintain a simple code-fence state machine to only accumulate code
        poe_inside_code_block = False
        poe_partial_buffer = ""
        for chunk in completion:
            # Handle different response formats for Mistral vs others
            chunk_content = None
            if _current_model["id"] in ("codestral-2508", "mistral-medium-2508"):
                # Mistral format: chunk.data.choices[0].delta.content
                if (
                    hasattr(chunk, "data") and chunk.data and
                    hasattr(chunk.data, "choices") and chunk.data.choices and 
                    hasattr(chunk.data.choices[0], "delta") and 
                    hasattr(chunk.data.choices[0].delta, "content") and 
                    chunk.data.choices[0].delta.content is not None
                ):
                    chunk_content = chunk.data.choices[0].delta.content
            else:
                # OpenAI format: chunk.choices[0].delta.content
                if (
                    hasattr(chunk, "choices") and chunk.choices and 
                    hasattr(chunk.choices[0], "delta") and 
                    hasattr(chunk.choices[0].delta, "content") and 
                    chunk.choices[0].delta.content is not None
                ):
                    chunk_content = chunk.choices[0].delta.content
            
            if chunk_content:
                # Ensure chunk_content is always a string to avoid regex errors
                if not isinstance(chunk_content, str):
                    # Handle structured thinking chunks (like ThinkChunk objects from magistral)
                    chunk_str = str(chunk_content) if chunk_content is not None else ""
                    if '[ThinkChunk(' in chunk_str:
                        # This is a structured thinking chunk, skip it to avoid polluting output
                        continue
                    chunk_content = chunk_str
                if _current_model["id"] == "gpt-5":
                    # If this chunk is only placeholder thinking, surface a status update without polluting content
                    if is_placeholder_thinking_only(chunk_content):
                        status_line = extract_last_thinking_line(chunk_content)
                        yield {
                            code_output: gr.update(value=(content or "") + "\n<!-- " + status_line + " -->", language="html"),
                            history_output: history_to_chatbot_messages(_history),
                        }
                        continue
                    # Filter placeholders
                    incoming = strip_placeholder_thinking(chunk_content)
                    # Process code fences incrementally, only keep content inside fences
                    s = poe_partial_buffer + incoming
                    append_text = ""
                    i = 0
                    # Find all triple backticks positions
                    for m in re.finditer(r"```", s):
                        if not poe_inside_code_block:
                            # Opening fence. Require a newline to confirm full opener so we can skip optional language line
                            nl = s.find("\n", m.end())
                            if nl == -1:
                                # Incomplete opener; buffer from this fence and wait for more
                                poe_partial_buffer = s[m.start():]
                                s = None
                                break
                            # Enter code, skip past newline after optional language token
                            poe_inside_code_block = True
                            i = nl + 1
                        else:
                            # Closing fence, append content inside and exit code
                            append_text += s[i:m.start()]
                            poe_inside_code_block = False
                            i = m.end()
                    if s is not None:
                        if poe_inside_code_block:
                            append_text += s[i:]
                            poe_partial_buffer = ""
                        else:
                            poe_partial_buffer = s[i:]
                    if append_text:
                        content += append_text
                else:
                    # Append content, filtering out placeholder thinking lines
                    content += strip_placeholder_thinking(chunk_content)
                search_status = ""
                
                # Handle transformers.js output differently
                if language == "transformers.js":
                    files = parse_transformers_js_output(content)

                    # Stream ALL code by merging current parts into a single HTML (inline CSS & JS)
                    has_any_part = any([files.get('index.html'), files.get('index.js'), files.get('style.css')])
                    if has_any_part:
                        merged_html = build_transformers_inline_html(files)
                        preview_val = None
                        if files['index.html'] and files['index.js'] and files['style.css']:
                            preview_val = send_transformers_to_sandbox(files)
                        yield {
                            code_output: gr.update(value=merged_html, language="html"),
                            history_output: history_to_chatbot_messages(_history),
                        }
                    elif has_existing_content:
                        # Model is returning search/replace changes for transformers.js - apply them
                        last_content = _history[-1][1] if _history and len(_history[-1]) > 1 else ""
                        modified_content = apply_transformers_js_search_replace_changes(last_content, content)
                        _mf = parse_transformers_js_output(modified_content)
                        yield {
                            code_output: gr.update(value=modified_content, language="html"),
                            history_output: history_to_chatbot_messages(_history),
                        }
                    else:
                        # Still streaming, show partial content
                        yield {
                            code_output: gr.update(value=content, language="html"),
                            history_output: history_to_chatbot_messages(_history),
                        }
                else:
                    clean_code = remove_code_block(content)
                    if has_existing_content:
                        # Handle modification of existing content
                        if clean_code.strip().startswith("<!DOCTYPE html>") or clean_code.strip().startswith("<html"):
                            # Model returned a complete HTML file
                            preview_val = None
                            if language == "html":
                                _mpc3 = parse_multipage_html_output(clean_code)
                                _mpc3 = validate_and_autofix_files(_mpc3)
                                preview_val = send_to_sandbox(inline_multipage_into_single_preview(_mpc3)) if _mpc3.get('index.html') else send_to_sandbox(clean_code)
                            elif language == "python" and is_streamlit_code(clean_code):
                                preview_val = send_streamlit_to_stlite(clean_code)
                            elif language == "gradio" or (language == "python" and is_gradio_code(clean_code)):
                                preview_val = send_gradio_to_lite(clean_code)
                            yield {
                                code_output: gr.update(value=clean_code, language=get_gradio_language(language)),
                                history_output: history_to_chatbot_messages(_history),
                            }
                        else:
                            # Model returned search/replace changes - apply them
                            last_content = _history[-1][1] if _history and len(_history[-1]) > 1 else ""
                            modified_content = apply_search_replace_changes(last_content, clean_code)
                            clean_content = remove_code_block(modified_content)
                            preview_val = None
                            if language == "html":
                                _mpc4 = parse_multipage_html_output(clean_content)
                                _mpc4 = validate_and_autofix_files(_mpc4)
                                preview_val = send_to_sandbox(inline_multipage_into_single_preview(_mpc4)) if _mpc4.get('index.html') else send_to_sandbox(clean_content)
                            elif language == "python" and is_streamlit_code(clean_content):
                                preview_val = send_streamlit_to_stlite(clean_content)
                            elif language == "gradio" or (language == "python" and is_gradio_code(clean_content)):
                                preview_val = send_gradio_to_lite(clean_content)
                            yield {
                                code_output: gr.update(value=clean_content, language=get_gradio_language(language)),
                                history_output: history_to_chatbot_messages(_history),
                            }
                    else:
                        preview_val = None
                        if language == "html":
                            _mpc5 = parse_multipage_html_output(clean_code)
                            _mpc5 = validate_and_autofix_files(_mpc5)
                            preview_val = send_to_sandbox(inline_multipage_into_single_preview(_mpc5)) if _mpc5.get('index.html') else send_to_sandbox(clean_code)
                        elif language == "python" and is_streamlit_code(clean_code):
                            preview_val = send_streamlit_to_stlite(clean_code)
                        elif language == "gradio" or (language == "python" and is_gradio_code(clean_code)):
                            preview_val = send_gradio_to_lite(clean_code)
                        yield {
                            code_output: gr.update(value=clean_code, language=get_gradio_language(language)),
                            history_output: history_to_chatbot_messages(_history),
                        }
            # Skip chunks with empty choices (end of stream)
            # Do not treat as error
        # Handle response based on whether this is a modification or new generation
        if language == "transformers.js":
            # Handle transformers.js output
            files = parse_transformers_js_output(content)
            if files['index.html'] and files['index.js'] and files['style.css']:
                # Model returned complete transformers.js output
                formatted_output = format_transformers_js_output(files)
                _history.append([query, formatted_output])
                yield {
                    code_output: formatted_output,
                    history: _history,
                    history_output: history_to_chatbot_messages(_history),
                }
            elif has_existing_content:
                # Model returned search/replace changes for transformers.js - apply them
                last_content = _history[-1][1] if _history and len(_history[-1]) > 1 else ""
                modified_content = apply_transformers_js_search_replace_changes(last_content, content)
                _history.append([query, modified_content])
                _mf = parse_transformers_js_output(modified_content)
                yield {
                    code_output: modified_content,
                    history: _history,
                    history_output: history_to_chatbot_messages(_history),
                }
            else:
                # Fallback if parsing failed
                _history.append([query, content])
                yield {
                    code_output: content,
                    history: _history,
                    history_output: history_to_chatbot_messages(_history),
                }
        elif language == "gradio":
            # Handle Gradio output - check if it's multi-file format or single file
            if ('=== app.py ===' in content or '=== requirements.txt ===' in content):
                # Model returned multi-file Gradio output - ensure requirements.txt is present
                files = parse_multi_file_python_output(content)
                if files and 'app.py' in files:
                    # Check if requirements.txt is missing and auto-generate it
                    if 'requirements.txt' not in files:
                        import_statements = extract_import_statements(files['app.py'])
                        requirements_content = generate_requirements_txt_with_llm(import_statements)
                        files['requirements.txt'] = requirements_content
                        
                        # Reformat with the auto-generated requirements.txt
                        content = format_multi_file_python_output(files)
                
                _history.append([query, content])
                yield {
                    code_output: content,
                    history: _history,
                    history_output: history_to_chatbot_messages(_history),
                }
            elif has_existing_content:
                # Check if this is a followup that should maintain multi-file structure
                last_content = _history[-1][1] if _history and len(_history[-1]) > 1 else ""
                
                # If the original was multi-file but the response isn't, try to convert it
                if ('=== app.py ===' in last_content or '=== requirements.txt ===' in last_content):
                    # Original was multi-file, but response is single block - need to convert
                    if not ('=== app.py ===' in content or '=== requirements.txt ===' in content):
                        # Try to parse as single-block Gradio code and convert to multi-file format
                        clean_content = remove_code_block(content)
                        if 'import gradio' in clean_content or 'from gradio' in clean_content:
                            # This looks like Gradio code, convert to multi-file format
                            files = parse_multi_file_python_output(clean_content)
                            if not files:
                                # Single file - create multi-file structure
                                files = {'app.py': clean_content}
                                
                                # Extract requirements from imports
                                import_statements = extract_import_statements(clean_content)
                                requirements_content = generate_requirements_txt_with_llm(import_statements)
                                files['requirements.txt'] = requirements_content
                            
                            # Format as multi-file output
                            formatted_content = format_multi_file_python_output(files)
                            _history.append([query, formatted_content])
                            yield {
                                code_output: formatted_content,
                                history: _history,
                                history_output: history_to_chatbot_messages(_history),
                            }
                        else:
                            # Not Gradio code, apply search/replace
                            modified_content = apply_search_replace_changes(last_content, content)
                            _history.append([query, modified_content])
                            yield {
                                code_output: modified_content,
                                history: _history,
                                history_output: history_to_chatbot_messages(_history),
                            }
                    else:
                        # Response is already multi-file format
                        _history.append([query, content])
                        yield {
                            code_output: content,
                            history: _history,
                            history_output: history_to_chatbot_messages(_history),
                        }
                else:
                    # Original was single file, apply search/replace
                    modified_content = apply_search_replace_changes(last_content, content)
                    _history.append([query, modified_content])
                    yield {
                        code_output: modified_content,
                        history: _history,
                        history_output: history_to_chatbot_messages(_history),
                    }
            else:
                # Fallback - treat as single file Gradio app
                _history.append([query, content])
                yield {
                    code_output: content,
                    history: _history,
                    history_output: history_to_chatbot_messages(_history),
                }
        elif has_existing_content:
            # Handle modification of existing content
            final_code = remove_code_block(content)
            if final_code.strip().startswith("<!DOCTYPE html>") or final_code.strip().startswith("<html"):
                # Model returned a complete HTML file
                clean_content = final_code
            else:
                # Model returned search/replace changes - apply them
                last_content = _history[-1][1] if _history and len(_history[-1]) > 1 else ""
                modified_content = apply_search_replace_changes(last_content, final_code)
                clean_content = remove_code_block(modified_content)
            
            # Use clean content without media generation
            
            # Update history with the cleaned content
            _history.append([query, clean_content])
            yield {
                code_output: clean_content,
                history: _history,
                history_output: history_to_chatbot_messages(_history),
            }
        else:
            # Regular generation - use the content as is
            final_content = remove_code_block(content)
            
            # Use final content without media generation
            
            _history.append([query, final_content])
            
            # Generate deployment message instead of preview
            deploy_message = f"""
            <div style='padding: 2em; text-align: center; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; border-radius: 12px; box-shadow: 0 4px 20px rgba(16, 185, 129, 0.3);'>
                <h2 style='margin-top: 0; font-size: 2em;'>🎉 Code Generated Successfully!</h2>
                <p style='font-size: 1.2em; margin: 1em 0; opacity: 0.95;'>Your {language.upper()} application is ready to deploy!</p>
                
                <div style='background: rgba(255,255,255,0.15); padding: 1.5em; border-radius: 10px; margin: 1.5em 0;'>
                    <h3 style='margin-top: 0; font-size: 1.3em;'>🚀 Next Steps:</h3>
                    <div style='text-align: left; max-width: 500px; margin: 0 auto;'>
                        <p style='margin: 0.8em 0; font-size: 1.1em; display: flex; align-items: center;'>
                            <span style='background: rgba(255,255,255,0.2); border-radius: 50%; width: 24px; height: 24px; display: inline-flex; align-items: center; justify-content: center; margin-right: 10px; font-weight: bold;'>1</span>
                            Use the <strong>Deploy button</strong> in the sidebar
                        </p>
                        <p style='margin: 0.8em 0; font-size: 1.1em; display: flex; align-items: center;'>
                            <span style='background: rgba(255,255,255,0.2); border-radius: 50%; width: 24px; height: 24px; display: inline-flex; align-items: center; justify-content: center; margin-right: 10px; font-weight: bold;'>2</span>
                            Enter your app name below
                        </p>
                        <p style='margin: 0.8em 0; font-size: 1.1em; display: flex; align-items: center;'>
                            <span style='background: rgba(255,255,255,0.2); border-radius: 50%; width: 24px; height: 24px; display: inline-flex; align-items: center; justify-content: center; margin-right: 10px; font-weight: bold;'>3</span>
                            Click <strong>"Publish"</strong>
                        </p>
                        <p style='margin: 0.8em 0; font-size: 1.1em; display: flex; align-items: center;'>
                            <span style='background: rgba(255,255,255,0.2); border-radius: 50%; width: 24px; height: 24px; display: inline-flex; align-items: center; justify-content: center; margin-right: 10px; font-weight: bold;'>4</span>
                            Share your creation! 🌍
                        </p>
                    </div>
                </div>
                
                <p style='font-size: 1em; opacity: 0.9; margin-bottom: 0;'>
                    💡 Your app will be live on Hugging Face Spaces in seconds!
                </p>
            </div>
            """
            
            yield {
                code_output: final_content,
                history: _history,
                history_output: history_to_chatbot_messages(_history),
            }
    except Exception as e:
        error_message = f"Error: {str(e)}"
        yield {
            code_output: error_message,
            history_output: history_to_chatbot_messages(_history),
        }

# Deploy to Spaces logic

def add_anycoder_tag_to_readme(api, repo_id, app_port=None):
    """Download existing README, add anycoder tag and app_port if needed, and upload back.
    
    Args:
        api: HuggingFace API client
        repo_id: Repository ID
        app_port: Optional port number to set for Docker spaces (e.g., 7860 for React apps)
    """
    try:
        import tempfile
        import re
        
        # Download the existing README
        readme_path = api.hf_hub_download(
            repo_id=repo_id,
            filename="README.md",
            repo_type="space"
        )
        
        # Read the existing README content
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse frontmatter and content
        if content.startswith('---'):
            # Split frontmatter and body
            parts = content.split('---', 2)
            if len(parts) >= 3:
                frontmatter = parts[1].strip()
                body = parts[2] if len(parts) > 2 else ""
                
                # Check if tags already exist
                if 'tags:' in frontmatter:
                    # Add anycoder to existing tags if not present
                    if '- anycoder' not in frontmatter:
                        frontmatter = re.sub(r'(tags:\s*\n(?:\s*-\s*[^\n]+\n)*)', r'\1- anycoder\n', frontmatter)
                else:
                    # Add tags section with anycoder
                    frontmatter += '\ntags:\n- anycoder'
                
                # Add app_port if specified and not already present
                if app_port is not None and 'app_port:' not in frontmatter:
                    frontmatter += f'\napp_port: {app_port}'
                
                # Reconstruct the README
                new_content = f"---\n{frontmatter}\n---{body}"
            else:
                # Malformed frontmatter, just add tags at the end of frontmatter
                new_content = content.replace('---', '---\ntags:\n- anycoder\n---', 1)
        else:
            # No frontmatter, add it at the beginning
            app_port_line = f'\napp_port: {app_port}' if app_port else ''
            new_content = f"---\ntags:\n- anycoder{app_port_line}\n---\n\n{content}"
        
        # Upload the modified README
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding='utf-8') as f:
            f.write(new_content)
            temp_path = f.name
        
        api.upload_file(
            path_or_fileobj=temp_path,
            path_in_repo="README.md",
            repo_id=repo_id,
            repo_type="space"
        )
        
        import os
        os.unlink(temp_path)
        
    except Exception as e:
        print(f"Warning: Could not modify README.md to add anycoder tag: {e}")

def extract_import_statements(code):
    """Extract import statements from generated code."""
    import ast
    import re
    
    import_statements = []
    
    # Built-in Python modules to exclude
    builtin_modules = {
        'os', 'sys', 'json', 'time', 'datetime', 'random', 'math', 're', 'collections',
        'itertools', 'functools', 'pathlib', 'urllib', 'http', 'email', 'html', 'xml',
        'csv', 'tempfile', 'shutil', 'subprocess', 'threading', 'multiprocessing',
        'asyncio', 'logging', 'typing', 'base64', 'hashlib', 'secrets', 'uuid',
        'copy', 'pickle', 'io', 'contextlib', 'warnings', 'sqlite3', 'gzip', 'zipfile',
        'tarfile', 'socket', 'ssl', 'platform', 'getpass', 'pwd', 'grp', 'stat',
        'glob', 'fnmatch', 'linecache', 'traceback', 'inspect', 'keyword', 'token',
        'tokenize', 'ast', 'code', 'codeop', 'dis', 'py_compile', 'compileall',
        'importlib', 'pkgutil', 'modulefinder', 'runpy', 'site', 'sysconfig'
    }
    
    try:
        # Try to parse as Python AST
        tree = ast.parse(code)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name.split('.')[0]
                    if module_name not in builtin_modules and not module_name.startswith('_'):
                        import_statements.append(f"import {alias.name}")
            
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module.split('.')[0]
                    if module_name not in builtin_modules and not module_name.startswith('_'):
                        names = [alias.name for alias in node.names]
                        import_statements.append(f"from {node.module} import {', '.join(names)}")
    
    except SyntaxError:
        # Fallback: use regex to find import statements
        for line in code.split('\n'):
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                # Check if it's not a builtin module
                if line.startswith('import '):
                    module_name = line.split()[1].split('.')[0]
                elif line.startswith('from '):
                    module_name = line.split()[1].split('.')[0]
                
                if module_name not in builtin_modules and not module_name.startswith('_'):
                    import_statements.append(line)
    
    return list(set(import_statements))  # Remove duplicates

def generate_requirements_txt_with_llm(import_statements):
    """Generate requirements.txt content using LLM based on import statements."""
    if not import_statements:
        return "# No additional dependencies required\n"
    
    # Use a lightweight model for this task
    try:
        client = get_inference_client("zai-org/GLM-4.6", "auto")
        
        imports_text = '\n'.join(import_statements)
        
        prompt = f"""Based on the following Python import statements, generate a comprehensive requirements.txt file with all necessary and commonly used related packages:

{imports_text}

Instructions:
- Include the direct packages needed for the imports
- Include commonly used companion packages and dependencies for better functionality
- Use correct PyPI package names (e.g., PIL -> Pillow, sklearn -> scikit-learn)
- IMPORTANT: For diffusers, ALWAYS use: git+https://github.com/huggingface/diffusers
- IMPORTANT: For transformers, ALWAYS use: git+https://github.com/huggingface/transformers
- IMPORTANT: If diffusers is installed, also include transformers and sentencepiece as they usually go together
- Examples of comprehensive dependencies:
  * diffusers often needs: git+https://github.com/huggingface/transformers, sentencepiece, accelerate, torch, tokenizers
  * transformers often needs: accelerate, torch, tokenizers, datasets
  * gradio often needs: requests, Pillow for image handling
  * pandas often needs: numpy, openpyxl for Excel files
  * matplotlib often needs: numpy, pillow for image saving
  * sklearn often needs: numpy, scipy, joblib
  * streamlit often needs: pandas, numpy, requests
  * opencv-python often needs: numpy, pillow
  * fastapi often needs: uvicorn, pydantic
  * torch often needs: torchvision, torchaudio (if doing computer vision/audio)
- Include packages for common file formats if relevant (openpyxl, python-docx, PyPDF2)
- Do not include Python built-in modules
- Do not specify versions unless there are known compatibility issues
- One package per line
- If no external packages are needed, return "# No additional dependencies required"

🚨 CRITICAL OUTPUT FORMAT:
- Output ONLY the package names, one per line (plain text format)
- Do NOT use markdown formatting (no ```, no bold, no headings, no lists)
- Do NOT add any explanatory text before or after the package list
- Do NOT wrap the output in code blocks
- Just output raw package names as they would appear in requirements.txt

Generate a comprehensive requirements.txt that ensures the application will work smoothly:"""

        messages = [
            {"role": "system", "content": "You are a Python packaging expert specializing in creating comprehensive, production-ready requirements.txt files. Output ONLY plain text package names without any markdown formatting, code blocks, or explanatory text. Your goal is to ensure applications work smoothly by including not just direct dependencies but also commonly needed companion packages, popular extensions, and supporting libraries that developers typically need together."},
            {"role": "user", "content": prompt}
        ]
        
        response = client.chat.completions.create(
            model="zai-org/GLM-4.6",
            messages=messages,
            max_tokens=1024,
            temperature=0.1
        )
        
        requirements_content = response.choices[0].message.content.strip()
        
        # Clean up the response in case it includes extra formatting
        if '```' in requirements_content:
            # Use the existing remove_code_block function for consistent cleaning
            requirements_content = remove_code_block(requirements_content)
        
        # Enhanced cleanup for markdown and formatting
        lines = requirements_content.split('\n')
        clean_lines = []
        for line in lines:
            stripped_line = line.strip()
            
            # Skip lines that are markdown formatting
            if (stripped_line == '```' or 
                stripped_line.startswith('```') or
                stripped_line.startswith('#') and not stripped_line.startswith('# ') or  # Skip markdown headers but keep comments
                stripped_line.startswith('**') or  # Skip bold text
                stripped_line.startswith('*') and not stripped_line[1:2].isalnum() or  # Skip markdown lists but keep package names starting with *
                stripped_line.startswith('-') and not stripped_line[1:2].isalnum() or  # Skip markdown lists but keep package names starting with -
                stripped_line.startswith('===') or  # Skip section dividers
                stripped_line.startswith('---') or  # Skip horizontal rules
                stripped_line.lower().startswith('here') or  # Skip explanatory text
                stripped_line.lower().startswith('this') or  # Skip explanatory text
                stripped_line.lower().startswith('the') or  # Skip explanatory text
                stripped_line.lower().startswith('based on') or  # Skip explanatory text
                stripped_line == ''):  # Skip empty lines unless they're at natural boundaries
                continue
            
            # Keep lines that look like valid package specifications
            # Valid lines: package names, git+https://, comments starting with "# "
            if (stripped_line.startswith('# ') or  # Valid comments
                stripped_line.startswith('git+') or  # Git dependencies
                stripped_line[0].isalnum() or  # Package names start with alphanumeric
                '==' in stripped_line or  # Version specifications
                '>=' in stripped_line or  # Version specifications
                '<=' in stripped_line):  # Version specifications
                clean_lines.append(line)
        
        requirements_content = '\n'.join(clean_lines).strip()
        
        # Ensure it ends with a newline
        if requirements_content and not requirements_content.endswith('\n'):
            requirements_content += '\n'
            
        return requirements_content if requirements_content else "# No additional dependencies required\n"
        
    except Exception as e:
        # Fallback: simple extraction with basic mapping
        dependencies = set()
        special_cases = {
            'PIL': 'Pillow', 
            'sklearn': 'scikit-learn',
            'skimage': 'scikit-image',
            'bs4': 'beautifulsoup4'
        }
        
        for stmt in import_statements:
            if stmt.startswith('import '):
                module_name = stmt.split()[1].split('.')[0]
                package_name = special_cases.get(module_name, module_name)
                dependencies.add(package_name)
            elif stmt.startswith('from '):
                module_name = stmt.split()[1].split('.')[0]
                package_name = special_cases.get(module_name, module_name)
                dependencies.add(package_name)
        
        if dependencies:
            return '\n'.join(sorted(dependencies)) + '\n'
        else:
            return "# No additional dependencies required\n"

def wrap_html_in_gradio_app(html_code):
    # Escape triple quotes for safe embedding
    safe_html = html_code.replace('"""', r'\"\"\"')
    
    # Extract import statements and generate requirements.txt with LLM
    import_statements = extract_import_statements(html_code)
    requirements_comment = ""
    if import_statements:
        requirements_content = generate_requirements_txt_with_llm(import_statements)
        requirements_comment = (
            "# Generated requirements.txt content (create this file manually if needed):\n"
            + '\n'.join(f"# {line}" for line in requirements_content.strip().split('\n')) + '\n\n'
        )
    
    return (
        f'{requirements_comment}'
        'import gradio as gr\n\n'
        'def show_html():\n'
        f'    return """{safe_html}"""\n\n'
        'demo = gr.Interface(fn=show_html, inputs=None, outputs=gr.HTML())\n\n'
        'if __name__ == "__main__":\n'
        '    demo.launch()\n'
    )
def deploy_to_spaces(code):
    if not code or not code.strip():
        return  # Do nothing if code is empty
    # Wrap the HTML code in a Gradio app
    app_py = wrap_html_in_gradio_app(code.strip())
    base_url = "https://huggingface.co/new-space"
    params = urllib.parse.urlencode({
        "name": "new-space",
        "sdk": "gradio"
    })
    # Use urlencode for file params
    files_params = urllib.parse.urlencode({
        "files[0][path]": "app.py",
        "files[0][content]": app_py
    })
    full_url = f"{base_url}?{params}&{files_params}"
    webbrowser.open_new_tab(full_url)

def wrap_html_in_static_app(html_code):
    # For static Spaces, just use the HTML code as-is
    return html_code

def prettify_comfyui_json_for_html(json_content: str) -> str:
    """Convert ComfyUI JSON to prettified HTML display"""
    try:
        import json
        # Parse and prettify the JSON
        parsed_json = json.loads(json_content)
        prettified_json = json.dumps(parsed_json, indent=2, ensure_ascii=False)
        
        # Create HTML wrapper with syntax highlighting
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ComfyUI Workflow</title>
    <style>
        body {{
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            background-color: #1e1e1e;
            color: #d4d4d4;
            margin: 0;
            padding: 20px;
            line-height: 1.4;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2em;
        }}
        .header a {{
            color: #ffffff;
            text-decoration: none;
            font-weight: bold;
            opacity: 0.9;
        }}
        .header a:hover {{
            opacity: 1;
            text-decoration: underline;
        }}
        .json-container {{
            background-color: #2d2d30;
            border-radius: 8px;
            padding: 20px;
            overflow-x: auto;
            border: 1px solid #3e3e42;
        }}
        pre {{
            margin: 0;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .json-key {{
            color: #9cdcfe;
        }}
        .json-string {{
            color: #ce9178;
        }}
        .json-number {{
            color: #b5cea8;
        }}
        .json-boolean {{
            color: #569cd6;
        }}
        .json-null {{
            color: #569cd6;
        }}
        .copy-btn {{
            background: #007acc;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin-bottom: 10px;
            font-family: inherit;
        }}
        .copy-btn:hover {{
            background: #005a9e;
        }}
        .download-btn {{
            background: #28a745;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin-bottom: 10px;
            margin-left: 10px;
            font-family: inherit;
        }}
        .download-btn:hover {{
            background: #218838;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>ComfyUI Workflow</h1>
        <p>Built with <a href="https://huggingface.co/spaces/akhaliq/anycoder" target="_blank">anycoder</a></p>
    </div>
    
    <button class="copy-btn" onclick="copyToClipboard()">📋 Copy JSON</button>
    <button class="download-btn" onclick="downloadJSON()">💾 Download JSON</button>
    
    <div class="json-container">
        <pre id="json-content">{prettified_json}</pre>
    </div>

    <script>
        function copyToClipboard() {{
            const jsonContent = document.getElementById('json-content').textContent;
            navigator.clipboard.writeText(jsonContent).then(() => {{
                const btn = document.querySelector('.copy-btn');
                const originalText = btn.textContent;
                btn.textContent = '✅ Copied!';
                setTimeout(() => {{
                    btn.textContent = originalText;
                }}, 2000);
            }});
        }}

        function downloadJSON() {{
            const jsonContent = document.getElementById('json-content').textContent;
            const blob = new Blob([jsonContent], {{ type: 'application/json' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'comfyui_workflow.json';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }}

        // Add syntax highlighting
        function highlightJSON() {{
            const content = document.getElementById('json-content');
            let html = content.innerHTML;
            
            // Highlight different JSON elements
            html = html.replace(/"([^"]+)":/g, '<span class="json-key">"$1":</span>');
            html = html.replace(/: "([^"]*)"/g, ': <span class="json-string">"$1"</span>');
            html = html.replace(/: (-?\d+\.?\d*)/g, ': <span class="json-number">$1</span>');
            html = html.replace(/: (true|false)/g, ': <span class="json-boolean">$1</span>');
            html = html.replace(/: null/g, ': <span class="json-null">null</span>');
            
            content.innerHTML = html;
        }}

        // Apply syntax highlighting after page load
        window.addEventListener('load', highlightJSON);
    </script>
</body>
</html>"""
        return html_content
    except json.JSONDecodeError:
        # If it's not valid JSON, return as-is
        return json_content
    except Exception as e:
        print(f"Error prettifying ComfyUI JSON: {e}")
        return json_content

def check_hf_space_url(url: str) -> Tuple[bool, str | None, str | None]:
    """Check if URL is a valid Hugging Face Spaces URL and extract username/project"""
    import re
    
    # Pattern to match HF Spaces URLs (allows dots in space names)
    url_pattern = re.compile(
        r'^(https?://)?(huggingface\.co|hf\.co)/spaces/([\w.-]+)/([\w.-]+)$',
        re.IGNORECASE
    )
    
    match = url_pattern.match(url.strip())
    if match:
        username = match.group(3)
        project_name = match.group(4)
        return True, username, project_name
    return False, None, None

def detect_transformers_js_space(api, username: str, project_name: str) -> bool:
    """Check if a space is a transformers.js app by looking for the three key files"""
    try:
        from huggingface_hub import list_repo_files
        files = list_repo_files(repo_id=f"{username}/{project_name}", repo_type="space")
        
        # Check for the three transformers.js files
        has_index_html = any('index.html' in f for f in files)
        has_index_js = any('index.js' in f for f in files)
        has_style_css = any('style.css' in f for f in files)
        
        return has_index_html and has_index_js and has_style_css
    except:
        return False

def fetch_transformers_js_files(api, username: str, project_name: str) -> dict:
    """Fetch all three transformers.js files from a space"""
    files = {}
    file_names = ['index.html', 'index.js', 'style.css']
    
    for file_name in file_names:
        try:
            content_path = api.hf_hub_download(
                repo_id=f"{username}/{project_name}",
                filename=file_name,
                repo_type="space"
            )
            
            with open(content_path, 'r', encoding='utf-8') as f:
                files[file_name] = f.read()
        except:
            files[file_name] = ""
    
    return files

def combine_transformers_js_files(files: dict, username: str, project_name: str) -> str:
    """Combine transformers.js files into the expected format for the LLM"""
    combined = f"""IMPORTED PROJECT FROM HUGGING FACE SPACE
==============================================

Space: {username}/{project_name}
SDK: static (transformers.js)
Type: Transformers.js Application

"""
    
    if files.get('index.html'):
        combined += f"=== index.html ===\n{files['index.html']}\n\n"
    
    if files.get('index.js'):
        combined += f"=== index.js ===\n{files['index.js']}\n\n"
    
    if files.get('style.css'):
        combined += f"=== style.css ===\n{files['style.css']}\n\n"
    
    return combined

def fetch_all_space_files(api, username: str, project_name: str, sdk: str) -> dict:
    """Fetch all relevant files from a Hugging Face Space"""
    files = {}
    
    try:
        from huggingface_hub import list_repo_files
        all_files = list_repo_files(repo_id=f"{username}/{project_name}", repo_type="space")
        
        # Filter out unwanted files
        relevant_files = []
        for file in all_files:
            # Skip hidden files, git files, and certain extensions
            if (file.startswith('.') or 
                file.endswith('.md') or 
                (file.endswith('.txt') and file not in ['requirements.txt', 'packages.txt']) or
                file.endswith('.log') or
                file.endswith('.pyc') or
                '__pycache__' in file):
                continue
            relevant_files.append(file)
        
        # Define priority files based on SDK
        priority_files = []
        if sdk == "gradio":
            priority_files = ["app.py", "main.py", "gradio_app.py", "requirements.txt", "packages.txt"]
        elif sdk == "streamlit":
            priority_files = ["streamlit_app.py", "app.py", "main.py", "requirements.txt", "packages.txt"]
        elif sdk == "static":
            priority_files = ["index.html", "index.js", "style.css", "script.js"]
        
        # Add priority files first, then other Python files, then other files
        files_to_fetch = []
        
        # Add priority files that exist
        for pfile in priority_files:
            if pfile in relevant_files:
                files_to_fetch.append(pfile)
                relevant_files.remove(pfile)
        
        # Add other Python files
        python_files = [f for f in relevant_files if f.endswith('.py')]
        files_to_fetch.extend(python_files)
        for pf in python_files:
            if pf in relevant_files:
                relevant_files.remove(pf)
        
        # Add other important files (JS, CSS, JSON, etc.)
        other_important = [f for f in relevant_files if any(f.endswith(ext) for ext in ['.js', '.css', '.json', '.html', '.yml', '.yaml'])]
        files_to_fetch.extend(other_important)
        
        # Limit to reasonable number of files to avoid overwhelming
        files_to_fetch = files_to_fetch[:20]  # Max 20 files
        
        # Download each file
        for file_name in files_to_fetch:
            try:
                content_path = api.hf_hub_download(
                    repo_id=f"{username}/{project_name}",
                    filename=file_name,
                    repo_type="space"
                )
                
                # Read file content with appropriate encoding
                try:
                    with open(content_path, 'r', encoding='utf-8') as f:
                        files[file_name] = f.read()
                except UnicodeDecodeError:
                    # For binary files or files with different encoding
                    with open(content_path, 'rb') as f:
                        content = f.read()
                        # Skip binary files that are too large or not text
                        if len(content) > 100000:  # Skip files > 100KB
                            files[file_name] = f"[Binary file: {file_name} - {len(content)} bytes]"
                        else:
                            try:
                                files[file_name] = content.decode('utf-8')
                            except:
                                files[file_name] = f"[Binary file: {file_name} - {len(content)} bytes]"
            except Exception as e:
                files[file_name] = f"[Error loading {file_name}: {str(e)}]"
                
    except Exception as e:
        # Fallback to single file loading
        return {}
    
    return files

def format_multi_file_space(files: dict, username: str, project_name: str, sdk: str) -> str:
    """Format multiple files from a space into a readable format"""
    if not files:
        return ""
    
    header = f"""IMPORTED PROJECT FROM HUGGING FACE SPACE
==============================================

Space: {username}/{project_name}
SDK: {sdk}
Files: {len(files)} files loaded

"""
    
    # Sort files to show main files first
    main_files = []
    other_files = []
    
    priority_order = ["app.py", "main.py", "streamlit_app.py", "gradio_app.py", "index.html", "requirements.txt"]
    
    for priority_file in priority_order:
        if priority_file in files:
            main_files.append(priority_file)
    
    for file_name in sorted(files.keys()):
        if file_name not in main_files:
            other_files.append(file_name)
    
    content = header
    
    # Add main files first
    for file_name in main_files:
        content += f"=== {file_name} ===\n{files[file_name]}\n\n"
    
    # Add other files
    for file_name in other_files:
        content += f"=== {file_name} ===\n{files[file_name]}\n\n"
    
    return content

def fetch_hf_space_content(username: str, project_name: str) -> str:
    """Fetch content from a Hugging Face Space"""
    try:
        import requests
        from huggingface_hub import HfApi
        
        # Try to get space info first
        api = HfApi()
        space_info = api.space_info(f"{username}/{project_name}")
        
        # Check if this is a transformers.js space first
        if space_info.sdk == "static" and detect_transformers_js_space(api, username, project_name):
            files = fetch_transformers_js_files(api, username, project_name)
            return combine_transformers_js_files(files, username, project_name)
        
        # Use the new multi-file loading approach for all space types
        sdk = space_info.sdk
        files = fetch_all_space_files(api, username, project_name, sdk)
        
        if files:
            # Use the multi-file format
            return format_multi_file_space(files, username, project_name, sdk)
        else:
            # Fallback to single file loading for compatibility
            main_file = None
            
            # Define file patterns to try based on SDK
            if sdk == "static":
                file_patterns = ["index.html"]
            elif sdk == "gradio":
                file_patterns = ["app.py", "main.py", "gradio_app.py"]
            elif sdk == "streamlit":
                file_patterns = ["streamlit_app.py", "src/streamlit_app.py", "app.py", "src/app.py", "main.py", "src/main.py", "Home.py", "src/Home.py", "🏠_Home.py", "src/🏠_Home.py", "1_🏠_Home.py", "src/1_🏠_Home.py"]
            else:
                # Try common files for unknown SDKs
                file_patterns = ["app.py", "src/app.py", "index.html", "streamlit_app.py", "src/streamlit_app.py", "main.py", "src/main.py", "Home.py", "src/Home.py"]
            
            # Try to find and download the main file
            for file in file_patterns:
                try:
                    content = api.hf_hub_download(
                        repo_id=f"{username}/{project_name}",
                        filename=file,
                        repo_type="space"
                    )
                    main_file = file
                    break
                except:
                    continue
            
            if main_file:
                content = api.hf_hub_download(
                    repo_id=f"{username}/{project_name}",
                    filename=main_file,
                    repo_type="space"
                )
                
                # Read the file content
                with open(content, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                return f"""IMPORTED PROJECT FROM HUGGING FACE SPACE
==============================================

Space: {username}/{project_name}
SDK: {sdk}
Main File: {main_file}

{file_content}"""
            else:
                # Try to get more information about available files for debugging
                try:
                    from huggingface_hub import list_repo_files
                    files_list = list_repo_files(repo_id=f"{username}/{project_name}", repo_type="space")
                    available_files = [f for f in files_list if not f.startswith('.') and not f.endswith('.md')]
                    return f"Error: Could not find main file in space {username}/{project_name}.\n\nSDK: {sdk}\nAvailable files: {', '.join(available_files[:10])}{'...' if len(available_files) > 10 else ''}\n\nTried looking for: {', '.join(file_patterns)}"
                except:
                    return f"Error: Could not find main file in space {username}/{project_name}. Expected files for {sdk} SDK: {', '.join(file_patterns) if 'file_patterns' in locals() else 'standard files'}"
            
    except Exception as e:
        return f"Error fetching space content: {str(e)}"

def load_project_from_url(url: str) -> Tuple[str, str]:
    """Load project from Hugging Face Space URL"""
    # Validate URL
    is_valid, username, project_name = check_hf_space_url(url)
    
    if not is_valid:
        return "Error: Please enter a valid Hugging Face Spaces URL.\n\nExpected format: https://huggingface.co/spaces/username/project", ""
    
    # Fetch content
    content = fetch_hf_space_content(username, project_name)
    
    if content.startswith("Error:"):
        return content, ""
    
    # Extract the actual code content by removing metadata
    lines = content.split('\n')
    code_start = 0
    for i, line in enumerate(lines):
        # Skip metadata lines and find the start of actual code
        if (line.strip() and 
            not line.startswith('=') and 
            not line.startswith('IMPORTED PROJECT') and
            not line.startswith('Space:') and
            not line.startswith('SDK:') and
            not line.startswith('Main File:')):
            code_start = i
            break
    
    code_content = '\n'.join(lines[code_start:])
    
    return f"✅ Successfully imported project from {username}/{project_name}", code_content

# -------- Repo/Model Import (GitHub & Hugging Face model) --------
def _parse_repo_or_model_url(url: str) -> Tuple[str, Optional[dict]]:
    """Parse a URL and detect if it's a GitHub repo, HF Space, or HF Model.

    Returns a tuple of (kind, meta) where kind in {"github", "hf_space", "hf_model", "unknown"}
    Meta contains parsed identifiers.
    """
    try:
        parsed = urlparse(url.strip())
        netloc = (parsed.netloc or "").lower()
        path = (parsed.path or "").strip("/")
        # Hugging Face spaces
        if ("huggingface.co" in netloc or netloc.endswith("hf.co")) and path.startswith("spaces/"):
            parts = path.split("/")
            if len(parts) >= 3:
                return "hf_space", {"username": parts[1], "project": parts[2]}
        # Hugging Face model repo (default)
        if ("huggingface.co" in netloc or netloc.endswith("hf.co")) and not path.startswith(("spaces/", "datasets/", "organizations/")):
            parts = path.split("/")
            if len(parts) >= 2:
                repo_id = f"{parts[0]}/{parts[1]}"
                return "hf_model", {"repo_id": repo_id}
        # GitHub repo
        if "github.com" in netloc:
            parts = path.split("/")
            if len(parts) >= 2:
                return "github", {"owner": parts[0], "repo": parts[1]}
    except Exception:
        pass
    return "unknown", None

def _fetch_hf_model_readme(repo_id: str) -> str | None:
    """Fetch README.md (model card) for a Hugging Face model repo."""
    try:
        api = HfApi()
        # Try direct README.md first
        try:
            local_path = api.hf_hub_download(repo_id=repo_id, filename="README.md", repo_type="model")
            with open(local_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            # Some repos use README at root without explicit type
            local_path = api.hf_hub_download(repo_id=repo_id, filename="README.md")
            with open(local_path, "r", encoding="utf-8") as f:
                return f.read()
    except Exception:
        return None

def _fetch_github_readme(owner: str, repo: str) -> str | None:
    """Fetch README.md from a GitHub repo via raw URLs, trying HEAD/main/master."""
    bases = [
        f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/README.md",
        f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md",
        f"https://raw.githubusercontent.com/{owner}/{repo}/master/README.md",
    ]
    for url in bases:
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200 and resp.text:
                return resp.text
        except Exception:
            continue
    return None

def _extract_transformers_or_diffusers_snippet(markdown_text: str) -> Tuple[str | None, str | None]:
    """Extract the most relevant Python code block referencing transformers/diffusers from markdown.

    Returns (language, code). If not found, returns (None, None).
    """
    if not markdown_text:
        return None, None
    # Find fenced code blocks
    code_blocks = []
    import re as _re
    for match in _re.finditer(r"```([\w+-]+)?\s*\n([\s\S]*?)```", markdown_text, _re.IGNORECASE):
        lang = (match.group(1) or "").lower()
        code = match.group(2) or ""
        code_blocks.append((lang, code.strip()))
    # Filter for transformers/diffusers relevance
    def score_block(code: str) -> int:
        score = 0
        kws = [
            "from transformers", "import transformers", "pipeline(",
            "AutoModel", "AutoTokenizer", "text-generation",
            "from diffusers", "import diffusers", "DiffusionPipeline",
            "StableDiffusion", "UNet", "EulerDiscreteScheduler"
        ]
        for kw in kws:
            if kw in code:
                score += 1
        # Prefer longer, self-contained snippets
        score += min(len(code) // 200, 5)
        return score
    scored = sorted(
        [cb for cb in code_blocks if any(kw in cb[1] for kw in ["transformers", "diffusers", "pipeline(", "StableDiffusion"])],
        key=lambda x: score_block(x[1]),
        reverse=True,
    )
    if scored:
        return scored[0][0] or None, scored[0][1]
    return None, None

def _infer_task_from_context(snippet: str | None, pipeline_tag: str | None) -> str:
    """Infer a task string for transformers pipeline; fall back to provided pipeline_tag or 'text-generation'."""
    if pipeline_tag:
        return pipeline_tag
    if not snippet:
        return "text-generation"
    lowered = snippet.lower()
    task_hints = {
        "text-generation": ["text-generation", "automodelforcausallm"],
        "text2text-generation": ["text2text-generation", "t5forconditionalgeneration"],
        "fill-mask": ["fill-mask", "automodelformaskedlm"],
        "summarization": ["summarization"],
        "translation": ["translation"],
        "text-classification": ["text-classification", "sequenceclassification"],
        "automatic-speech-recognition": ["speechrecognition", "automatic-speech-recognition", "asr"],
        "image-classification": ["image-classification"],
        "zero-shot-image-classification": ["zero-shot-image-classification"],
    }
    for task, hints in task_hints.items():
        if any(h in lowered for h in hints):
            return task
    # Inspect explicit pipeline("task")
    import re as _re
    m = _re.search(r"pipeline\(\s*['\"]([\w\-]+)['\"]", snippet)
    if m:
        return m.group(1)
    return "text-generation"

def _generate_gradio_app_from_transformers(repo_id: str, task: str) -> str:
    """Build a minimal Gradio app using transformers.pipeline for a given model and task."""
    # Map simple UI per task; default to text in/out
    if task in {"text-generation", "text2text-generation", "summarization", "translation", "fill-mask"}:
        return (
            "import gradio as gr\n"
            "from transformers import pipeline\n\n"
            f"pipe = pipeline(task='{task}', model='{repo_id}')\n\n"
            "def infer(prompt, max_new_tokens=256, temperature=0.7, top_p=0.95):\n"
            "    if '\u2047' in prompt:\n"
            "        # Fill-mask often uses [MASK]; keep generic handling\n"
            "        pass\n"
            "    out = pipe(prompt, max_new_tokens=max_new_tokens, do_sample=True, temperature=temperature, top_p=top_p)\n"
            "    if isinstance(out, list):\n"
            "        if isinstance(out[0], dict):\n"
            "            return next(iter(out[0].values())) if out[0] else str(out)\n"
            "        return str(out[0])\n"
            "    return str(out)\n\n"
            "demo = gr.Interface(\n"
            "    fn=infer,\n"
            "    inputs=[gr.Textbox(label='Input', lines=8), gr.Slider(1, 2048, value=256, label='max_new_tokens'), gr.Slider(0.0, 1.5, value=0.7, step=0.01, label='temperature'), gr.Slider(0.0, 1.0, value=0.95, step=0.01, label='top_p')],\n"
            "    outputs=gr.Textbox(label='Output', lines=8),\n"
            "    title='Transformers Demo'\n"
            ")\n\n"
            "if __name__ == '__main__':\n"
            "    demo.launch()\n"
        )
    elif task in {"text-classification"}:
        return (
            "import gradio as gr\n"
            "from transformers import pipeline\n\n"
            f"pipe = pipeline(task='{task}', model='{repo_id}')\n\n"
            "def infer(text):\n"
            "    out = pipe(text)\n"
            "    # Expect list of dicts with label/score\n"
            "    return {o['label']: float(o['score']) for o in out}\n\n"
            "demo = gr.Interface(fn=infer, inputs=gr.Textbox(lines=6), outputs=gr.Label(), title='Text Classification')\n\n"
            "if __name__ == '__main__':\n"
            "    demo.launch()\n"
        )
    else:
        # Fallback generic text pipeline (pipeline infers task from model config)
        return (
            "import gradio as gr\n"
            "from transformers import pipeline\n\n"
            f"pipe = pipeline(model='{repo_id}')\n\n"
            "def infer(prompt):\n"
            "    out = pipe(prompt)\n"
            "    if isinstance(out, list):\n"
            "        if isinstance(out[0], dict):\n"
            "            return next(iter(out[0].values())) if out[0] else str(out)\n"
            "        return str(out[0])\n"
            "    return str(out)\n\n"
            "demo = gr.Interface(fn=infer, inputs=gr.Textbox(lines=8), outputs=gr.Textbox(lines=8), title='Transformers Demo')\n\n"
            "if __name__ == '__main__':\n"
            "    demo.launch()\n"
        )

def _generate_gradio_app_from_diffusers(repo_id: str) -> str:
    """Build a minimal Gradio app for text-to-image using diffusers."""
    return (
        "import gradio as gr\n"
        "import torch\n"
        "from diffusers import DiffusionPipeline\n\n"
        f"pipe = DiffusionPipeline.from_pretrained('{repo_id}')\n"
        "device = 'cuda' if torch.cuda.is_available() else 'cpu'\n"
        "pipe = pipe.to(device)\n\n"
        "def infer(prompt, guidance_scale=7.0, num_inference_steps=30, seed=0):\n"
        "    generator = None if seed == 0 else torch.Generator(device=device).manual_seed(int(seed))\n"
        "    image = pipe(prompt, guidance_scale=float(guidance_scale), num_inference_steps=int(num_inference_steps), generator=generator).images[0]\n"
        "    return image\n\n"
        "demo = gr.Interface(\n"
        "    fn=infer,\n"
        "    inputs=[gr.Textbox(label='Prompt'), gr.Slider(0.0, 15.0, value=7.0, step=0.1, label='guidance_scale'), gr.Slider(1, 100, value=30, step=1, label='num_inference_steps'), gr.Slider(0, 2**32-1, value=0, step=1, label='seed')],\n"
        "    outputs=gr.Image(type='pil'),\n"
        "    title='Diffusers Text-to-Image'\n"
        ")\n\n"
        "if __name__ == '__main__':\n"
        "    demo.launch()\n"
    )

def import_repo_to_app(url: str, framework: str = "Gradio") -> Tuple[str, str, str]:
    """Import a GitHub or HF model repo and return the raw code snippet from README/model card.

    Returns (status_markdown, code_snippet, preview_html). Preview left empty; UI will decide.
    """
    if not url or not url.strip():
        return "Please enter a repository URL.", "", ""
    kind, meta = _parse_repo_or_model_url(url)
    if kind == "hf_space" and meta:
        # Spaces already contain runnable apps; keep existing behavior to fetch main file raw
        status, code = load_project_from_url(url)
        return status, code, ""
    # Fetch markdown
    markdown = None
    repo_id = None
    pipeline_tag = None
    library_name = None
    if kind == "hf_model" and meta:
        repo_id = meta.get("repo_id")
        # Try model info to get pipeline tag/library
        try:
            api = HfApi()
            info = api.model_info(repo_id)
            pipeline_tag = getattr(info, "pipeline_tag", None)
            library_name = getattr(info, "library_name", None)
        except Exception:
            pass
        markdown = _fetch_hf_model_readme(repo_id)
    elif kind == "github" and meta:
        markdown = _fetch_github_readme(meta.get("owner"), meta.get("repo"))
    else:
        return "Error: Unsupported or invalid URL. Provide a GitHub repo or Hugging Face model URL.", "", ""

    if not markdown:
        return "Error: Could not fetch README/model card.", "", ""

    lang, snippet = _extract_transformers_or_diffusers_snippet(markdown)
    if not snippet:
        return "Error: No relevant transformers/diffusers code block found in README/model card.", "", ""

    status = "✅ Imported code snippet from README/model card. Use it as a starting point."
    return status, snippet, ""

# Gradio Theme Configurations with proper theme objects
def get_saved_theme():
    """Get the saved theme preference from file"""
    try:
        if os.path.exists('.theme_preference'):
            with open('.theme_preference', 'r') as f:
                return f.read().strip()
    except:
        pass
    return "Developer"
def save_theme_preference(theme_name):
    """Save theme preference to file"""
    try:
        with open('.theme_preference', 'w') as f:
            f.write(theme_name)
    except:
        pass

THEME_CONFIGS = {
    "Default": {
        "theme": gr.themes.Default(),
        "description": "Gradio's standard theme with clean orange accents"
    },
    "Base": {
        "theme": gr.themes.Base(
            primary_hue="blue",
            secondary_hue="slate",
            neutral_hue="slate",
            text_size="sm",
            spacing_size="sm",
            radius_size="md"
        ),
        "description": "Minimal foundation theme with blue accents"
    },
    "Soft": {
        "theme": gr.themes.Soft(
            primary_hue="emerald",
            secondary_hue="emerald",
            neutral_hue="slate",
            text_size="sm",
            spacing_size="md",
            radius_size="lg"
        ),
        "description": "Gentle rounded theme with soft emerald colors"
    },
    "Monochrome": {
        "theme": gr.themes.Monochrome(
            primary_hue="slate",
            secondary_hue="slate",
            neutral_hue="slate",
            text_size="sm",
            spacing_size="sm",
            radius_size="sm"
        ),
        "description": "Elegant black and white design"
    },
    "Glass": {
        "theme": gr.themes.Glass(
            primary_hue="blue",
            secondary_hue="blue",
            neutral_hue="slate",
            text_size="sm",
            spacing_size="md",
            radius_size="lg"
        ),
        "description": "Modern glassmorphism with blur effects"
    },
    "Dark Ocean": {
        "theme": gr.themes.Base(
            primary_hue="blue",
            secondary_hue="slate", 
            neutral_hue="slate",
            text_size="sm",
            spacing_size="sm",
            radius_size="md"
        ).set(
            body_background_fill="#0f172a",
            body_background_fill_dark="#0f172a",
            background_fill_primary="#3b82f6",
            background_fill_secondary="#1e293b",
            border_color_primary="#334155",
            block_background_fill="#1e293b",
            block_border_color="#334155",
            body_text_color="#f1f5f9",
            body_text_color_dark="#f1f5f9",
            block_label_text_color="#f1f5f9",
            block_label_text_color_dark="#f1f5f9",
            block_title_text_color="#f1f5f9",
            block_title_text_color_dark="#f1f5f9",
            input_background_fill="#0f172a",
            input_background_fill_dark="#0f172a",
            input_border_color="#334155",
            input_border_color_dark="#334155",
            button_primary_background_fill="#3b82f6",
            button_primary_border_color="#3b82f6",
            button_secondary_background_fill="#334155",
            button_secondary_border_color="#475569"
        ),
        "description": "Deep blue dark theme perfect for coding"
    },
    "Cyberpunk": {
        "theme": gr.themes.Base(
            primary_hue="fuchsia",
            secondary_hue="cyan",
            neutral_hue="slate",
            text_size="sm",
            spacing_size="sm",
            radius_size="none",
            font="Orbitron"
        ).set(
            body_background_fill="#0a0a0f",
            body_background_fill_dark="#0a0a0f",
            background_fill_primary="#ff10f0",
            background_fill_secondary="#1a1a2e",
            border_color_primary="#00f5ff",
            block_background_fill="#1a1a2e",
            block_border_color="#00f5ff",
            body_text_color="#00f5ff",
            body_text_color_dark="#00f5ff",
            block_label_text_color="#ff10f0",
            block_label_text_color_dark="#ff10f0",
            block_title_text_color="#ff10f0",
            block_title_text_color_dark="#ff10f0",
            input_background_fill="#0a0a0f",
            input_background_fill_dark="#0a0a0f",
            input_border_color="#00f5ff",
            input_border_color_dark="#00f5ff",
            button_primary_background_fill="#ff10f0",
            button_primary_border_color="#ff10f0",
            button_secondary_background_fill="#1a1a2e",
            button_secondary_border_color="#00f5ff"
        ),
        "description": "Futuristic neon cyber aesthetics"
    },
    "Forest": {
        "theme": gr.themes.Soft(
            primary_hue="emerald",
            secondary_hue="green",
            neutral_hue="emerald",
            text_size="sm",
            spacing_size="md",
            radius_size="lg"
        ).set(
            body_background_fill="#f0fdf4",
            body_background_fill_dark="#064e3b",
            background_fill_primary="#059669",
            background_fill_secondary="#ecfdf5",
            border_color_primary="#bbf7d0",
            block_background_fill="#ffffff",
            block_border_color="#d1fae5",
            body_text_color="#064e3b",
            body_text_color_dark="#f0fdf4",
            block_label_text_color="#064e3b",
            block_label_text_color_dark="#f0fdf4",
            block_title_text_color="#059669",
            block_title_text_color_dark="#10b981"
        ),
        "description": "Nature-inspired green earth tones"
    },
    "High Contrast": {
        "theme": gr.themes.Base(
            primary_hue="yellow",
            secondary_hue="slate",
            neutral_hue="slate",
            text_size="lg",
            spacing_size="lg",
            radius_size="sm"
        ).set(
            body_background_fill="#ffffff",
            body_background_fill_dark="#ffffff",
            background_fill_primary="#000000",
            background_fill_secondary="#ffffff",
            border_color_primary="#000000",
            block_background_fill="#ffffff",
            block_border_color="#000000",
            body_text_color="#000000",
            body_text_color_dark="#000000",
            block_label_text_color="#000000",
            block_label_text_color_dark="#000000",
            block_title_text_color="#000000",
            block_title_text_color_dark="#000000",
            input_background_fill="#ffffff",
            input_background_fill_dark="#ffffff",
            input_border_color="#000000",
            input_border_color_dark="#000000",
            button_primary_background_fill="#ffff00",
            button_primary_border_color="#000000",
            button_secondary_background_fill="#ffffff",
            button_secondary_border_color="#000000"
        ),
        "description": "Accessibility-focused high visibility"
    },
    "Developer": {
        "theme": gr.themes.Base(
            primary_hue="blue",
            secondary_hue="slate",
            neutral_hue="slate",
            text_size="sm",
            spacing_size="sm",
            radius_size="sm",
            font="Consolas"
        ).set(
            # VS Code exact colors
            body_background_fill="#1e1e1e",           # VS Code editor background
            body_background_fill_dark="#1e1e1e",
            background_fill_primary="#007acc",        # VS Code blue accent
            background_fill_secondary="#252526",      # VS Code sidebar background
            border_color_primary="#3e3e42",          # VS Code border color
            block_background_fill="#252526",         # VS Code panel background
            block_border_color="#3e3e42",           # VS Code subtle borders
            body_text_color="#cccccc",               # VS Code default text
            body_text_color_dark="#cccccc",
            block_label_text_color="#cccccc",
            block_label_text_color_dark="#cccccc",
            block_title_text_color="#ffffff",        # VS Code active text
            block_title_text_color_dark="#ffffff",
            input_background_fill="#2d2d30",         # VS Code input background
            input_background_fill_dark="#2d2d30",
            input_border_color="#3e3e42",           # VS Code input border
            input_border_color_dark="#3e3e42",
            input_border_color_focus="#007acc",      # VS Code focus border
            input_border_color_focus_dark="#007acc",
            button_primary_background_fill="#007acc", # VS Code button blue
            button_primary_border_color="#007acc",
            button_primary_background_fill_hover="#0e639c", # VS Code button hover
            button_secondary_background_fill="#2d2d30",
            button_secondary_border_color="#3e3e42",
            button_secondary_text_color="#cccccc"
        ),
        "description": "Authentic VS Code dark theme with exact color matching"
    }
}

# Additional theme information for developers
THEME_FEATURES = {
    "Default": ["Orange accents", "Clean layout", "Standard Gradio look"],
    "Base": ["Blue accents", "Minimal styling", "Clean foundation"],
    "Soft": ["Rounded corners", "Emerald colors", "Comfortable viewing"],
    "Monochrome": ["Black & white", "High elegance", "Timeless design"],
    "Glass": ["Glassmorphism", "Blur effects", "Translucent elements"],
    "Dark Ocean": ["Deep blue palette", "Dark theme", "Easy on eyes"],
    "Cyberpunk": ["Neon cyan/magenta", "Futuristic fonts", "Cyber vibes"],
    "Forest": ["Nature inspired", "Green tones", "Organic rounded"],
    "High Contrast": ["Black/white/yellow", "High visibility", "Accessibility"],
    "Developer": ["Authentic VS Code colors", "Consolas/Monaco fonts", "Exact theme matching"]
}

# Load saved theme and apply it
current_theme_name = get_saved_theme()
current_theme = THEME_CONFIGS[current_theme_name]["theme"]

# Main application with proper Gradio theming
with gr.Blocks(
    title="AnyCoder - AI Code Generator",
    theme=current_theme,
    css="""
        .theme-info { font-size: 0.9em; opacity: 0.8; }
        .theme-description { padding: 8px 0; }
        .theme-status { 
            padding: 10px; 
            border-radius: 8px; 
            background: rgba(34, 197, 94, 0.1); 
            border: 1px solid rgba(34, 197, 94, 0.2); 
            margin: 8px 0; 
        }
        .restart-needed {
            padding: 12px;
            border-radius: 8px;
            background: rgba(255, 193, 7, 0.1);
            border: 1px solid rgba(255, 193, 7, 0.3);
            margin: 8px 0;
            text-align: center;
        }
        /* Authentication status styling */
        .auth-status {
            padding: 8px 12px;
            border-radius: 6px;
            margin: 8px 0;
            font-weight: 500;
            text-align: center;
        }
        .auth-status:has-text("🔒") {
            background: rgba(231, 76, 60, 0.1);
            border: 1px solid rgba(231, 76, 60, 0.3);
            color: #e74c3c;
        }
        .auth-status:has-text("✅") {
            background: rgba(46, 204, 113, 0.1);
            border: 1px solid rgba(46, 204, 113, 0.3);
            color: #2ecc71;
        }
    """
) as demo:
    history = gr.State([])
    setting = gr.State({
        "system": HTML_SYSTEM_PROMPT,
    })
    current_model = gr.State(DEFAULT_MODEL)
    open_panel = gr.State(None)
    last_login_state = gr.State(None)

    with gr.Sidebar() as sidebar:
        login_button = gr.LoginButton()
        
        


        # Unified Import section
        import_header_md = gr.Markdown("📥 Import Project (Space, GitHub, or Model)", visible=False)
        load_project_url = gr.Textbox(
            label="Project URL",
            placeholder="https://huggingface.co/spaces/user/space OR https://huggingface.co/user/model OR https://github.com/owner/repo",
            lines=1
        , visible=False)
        load_project_btn = gr.Button("📥 Import Project", variant="secondary", size="sm", visible=True)
        load_project_status = gr.Markdown(visible=False)
        
        input = gr.Textbox(
            label="What would you like to build?",
            placeholder="🔒 Please log in with Hugging Face to use AnyCoder...",
            lines=3,
            visible=True,
            interactive=False
        )
        # Language dropdown for code generation (add Streamlit and Gradio as first-class options)
        language_choices = [
            "html", "gradio", "transformers.js", "streamlit", "comfyui", "react"
        ]
        language_dropdown = gr.Dropdown(
            choices=language_choices,
            value="html",
            label="Code Language",
            visible=True
        )
        # Removed image generation components
        with gr.Row():
            btn = gr.Button("Generate", variant="secondary", size="lg", scale=2, visible=True, interactive=False)
            clear_btn = gr.Button("Clear", variant="secondary", size="sm", scale=1, visible=True)
        # --- Deploy components (visible by default) ---
        deploy_header_md = gr.Markdown("", visible=False)
        deploy_btn = gr.Button("Publish", variant="primary", visible=True)
        deploy_status = gr.Markdown(visible=False, label="Deploy status")
        # --- End move ---
        # Removed media generation and web search UI components

        # Removed media generation toggle event handlers
        model_dropdown = gr.Dropdown(
            choices=[model['name'] for model in AVAILABLE_MODELS],
            value=DEFAULT_MODEL_NAME,
            label="Model",
            visible=True
        )
        provider_state = gr.State("auto")
        # Removed web search availability indicator
        def on_model_change(model_name):
            for m in AVAILABLE_MODELS:
                if m['name'] == model_name:
                    return m
            return AVAILABLE_MODELS[0]
        def save_prompt(input):
            return {setting: {"system": input}}
        model_dropdown.change(
            lambda model_name: on_model_change(model_name),
            inputs=model_dropdown,
            outputs=[current_model]
        )
        # --- Remove deploy/app name/sdk from bottom column ---
        # (delete the gr.Column() block containing space_name_input, sdk_dropdown, deploy_btn, deploy_status)

    with gr.Column() as main_column:
        with gr.Tabs():
            with gr.Tab("Code"):
                code_output = gr.Code(
                    language="html", 
                    lines=25, 
                    interactive=True,
                    label="Generated code"
                )
                
                
                
            # Transformers.js multi-file editors (hidden by default)
            with gr.Group(visible=False) as tjs_group:
                with gr.Tabs():
                    with gr.Tab("index.html"):
                        tjs_html_code = gr.Code(language="html", lines=20, interactive=True, label="index.html")
                    with gr.Tab("index.js"):
                        tjs_js_code = gr.Code(language="javascript", lines=20, interactive=True, label="index.js")
                    with gr.Tab("style.css"):
                        tjs_css_code = gr.Code(language="css", lines=20, interactive=True, label="style.css")

            # Python multi-file editors (hidden by default) for Gradio/Streamlit
            with gr.Group(visible=False) as python_group_2:
                with gr.Tabs():
                    with gr.Tab("app.py") as python_tab_2_1:
                        python_code_2_1 = gr.Code(language="python", lines=20, interactive=True, label="app.py")
                    with gr.Tab("file 2") as python_tab_2_2:
                        python_code_2_2 = gr.Code(language="python", lines=18, interactive=True, label="file 2")
            
            with gr.Group(visible=False) as python_group_3:
                with gr.Tabs():
                    with gr.Tab("app.py") as python_tab_3_1:
                        python_code_3_1 = gr.Code(language="python", lines=20, interactive=True, label="app.py")
                    with gr.Tab("file 2") as python_tab_3_2:
                        python_code_3_2 = gr.Code(language="python", lines=18, interactive=True, label="file 2")
                    with gr.Tab("file 3") as python_tab_3_3:
                        python_code_3_3 = gr.Code(language="python", lines=18, interactive=True, label="file 3")
            
            with gr.Group(visible=False) as python_group_4:
                with gr.Tabs():
                    with gr.Tab("app.py") as python_tab_4_1:
                        python_code_4_1 = gr.Code(language="python", lines=20, interactive=True, label="app.py")
                    with gr.Tab("file 2") as python_tab_4_2:
                        python_code_4_2 = gr.Code(language="python", lines=18, interactive=True, label="file 2")
                    with gr.Tab("file 3") as python_tab_4_3:
                        python_code_4_3 = gr.Code(language="python", lines=18, interactive=True, label="file 3")
                    with gr.Tab("file 4") as python_tab_4_4:
                        python_code_4_4 = gr.Code(language="python", lines=18, interactive=True, label="file 4")
            
            with gr.Group(visible=False) as python_group_5plus:
                with gr.Tabs():
                    with gr.Tab("app.py") as python_tab_5_1:
                        python_code_5_1 = gr.Code(language="python", lines=20, interactive=True, label="app.py")
                    with gr.Tab("file 2") as python_tab_5_2:
                        python_code_5_2 = gr.Code(language="python", lines=18, interactive=True, label="file 2")
                    with gr.Tab("file 3") as python_tab_5_3:
                        python_code_5_3 = gr.Code(language="python", lines=18, interactive=True, label="file 3")
                    with gr.Tab("file 4") as python_tab_5_4:
                        python_code_5_4 = gr.Code(language="python", lines=18, interactive=True, label="file 4")
                    with gr.Tab("file 5") as python_tab_5_5:
                        python_code_5_5 = gr.Code(language="python", lines=18, interactive=True, label="file 5")
                
                # Static HTML multi-file editors (hidden by default). Use separate tab groups for different file counts.
                with gr.Group(visible=False) as static_group_2:
                    with gr.Tabs():
                        with gr.Tab("index.html") as static_tab_2_1:
                            static_code_2_1 = gr.Code(language="html", lines=20, interactive=True, label="index.html")
                        with gr.Tab("file 2") as static_tab_2_2:
                            static_code_2_2 = gr.Code(language="html", lines=18, interactive=True, label="file 2")
                
                with gr.Group(visible=False) as static_group_3:
                    with gr.Tabs():
                        with gr.Tab("index.html") as static_tab_3_1:
                            static_code_3_1 = gr.Code(language="html", lines=20, interactive=True, label="index.html")
                        with gr.Tab("file 2") as static_tab_3_2:
                            static_code_3_2 = gr.Code(language="html", lines=18, interactive=True, label="file 2")
                        with gr.Tab("file 3") as static_tab_3_3:
                            static_code_3_3 = gr.Code(language="html", lines=18, interactive=True, label="file 3")
                
                with gr.Group(visible=False) as static_group_4:
                    with gr.Tabs():
                        with gr.Tab("index.html") as static_tab_4_1:
                            static_code_4_1 = gr.Code(language="html", lines=20, interactive=True, label="index.html")
                        with gr.Tab("file 2") as static_tab_4_2:
                            static_code_4_2 = gr.Code(language="html", lines=18, interactive=True, label="file 2")
                        with gr.Tab("file 3") as static_tab_4_3:
                            static_code_4_3 = gr.Code(language="html", lines=18, interactive=True, label="file 3")
                        with gr.Tab("file 4") as static_tab_4_4:
                            static_code_4_4 = gr.Code(language="html", lines=18, interactive=True, label="file 4")
                
                with gr.Group(visible=False) as static_group_5plus:
                    with gr.Tabs():
                        with gr.Tab("index.html") as static_tab_5_1:
                            static_code_5_1 = gr.Code(language="html", lines=20, interactive=True, label="index.html")
                        with gr.Tab("file 2") as static_tab_5_2:
                            static_code_5_2 = gr.Code(language="html", lines=18, interactive=True, label="file 2")
                        with gr.Tab("file 3") as static_tab_5_3:
                            static_code_5_3 = gr.Code(language="html", lines=18, interactive=True, label="file 3")
                        with gr.Tab("file 4") as static_tab_5_4:
                            static_code_5_4 = gr.Code(language="html", lines=18, interactive=True, label="file 4")
                        with gr.Tab("file 5") as static_tab_5_5:
                            static_code_5_5 = gr.Code(language="html", lines=18, interactive=True, label="file 5")
            # React Next.js multi-file editors (hidden by default)
            with gr.Group(visible=False) as react_group:
                with gr.Tabs():
                    with gr.Tab("Dockerfile"):
                        react_code_dockerfile = gr.Code(language="dockerfile", lines=15, interactive=True, label="Dockerfile")
                    with gr.Tab("package.json"):
                        react_code_package_json = gr.Code(language="json", lines=20, interactive=True, label="package.json")
                    with gr.Tab("next.config.js"):
                        react_code_next_config = gr.Code(language="javascript", lines=15, interactive=True, label="next.config.js")
                    with gr.Tab("postcss.config.js"):
                        react_code_postcss_config = gr.Code(language="javascript", lines=10, interactive=True, label="postcss.config.js")
                    with gr.Tab("tailwind.config.js"):
                        react_code_tailwind_config = gr.Code(language="javascript", lines=15, interactive=True, label="tailwind.config.js")
                    with gr.Tab("pages/_app.js"):
                        react_code_pages_app = gr.Code(language="javascript", lines=15, interactive=True, label="pages/_app.js")
                    with gr.Tab("pages/index.js"):
                        react_code_pages_index = gr.Code(language="javascript", lines=20, interactive=True, label="pages/index.js")
                    with gr.Tab("components/ChatApp.jsx"):
                        react_code_components = gr.Code(language="javascript", lines=25, interactive=True, label="components/ChatApp.jsx")
                    with gr.Tab("styles/globals.css"):
                        react_code_styles = gr.Code(language="css", lines=20, interactive=True, label="styles/globals.css")

            # Removed Import Logs tab for cleaner UI
            # History tab hidden per user request
            # with gr.Tab("History"):
            #     history_output = gr.Chatbot(show_label=False, height=400, type="messages")
        
        # Keep history_output as hidden component to maintain functionality
        history_output = gr.Chatbot(show_label=False, height=400, type="messages", visible=False)

    # Global generation status view (disabled placeholder)
    generating_status = gr.Markdown("", visible=False)

    # Unified import handler
    def handle_import_project(url):
        if not url.strip():
            return [
                gr.update(value="Please enter a URL.", visible=True),
                gr.update(),
                gr.update(),
                [],
                [],
                gr.update(value="Publish", visible=False),
                gr.update(),  # keep import header as-is
                gr.update(),  # keep import button as-is
                gr.update()   # language dropdown - no change
            ]

        kind, meta = _parse_repo_or_model_url(url)
        if kind == "hf_space":
            status, code = load_project_from_url(url)
            # Extract space info for deployment
            is_valid, username, project_name = check_hf_space_url(url)
            space_name = f"{username}/{project_name}" if is_valid else ""
            loaded_history = [[f"Imported Space from {url}", code]]
            
            # Determine the correct language/framework based on the imported content
            code_lang = "html"  # default
            framework_type = "html"  # for language dropdown
            
            # Check imports to determine framework for Python code
            if is_streamlit_code(code):
                code_lang = "python"
                framework_type = "streamlit"
            elif is_gradio_code(code):
                code_lang = "python"
                framework_type = "gradio"
            elif "=== index.html ===" in code and "=== index.js ===" in code and "=== style.css ===" in code:
                # This is a transformers.js app with the combined format
                code_lang = "html"  # Use html for code display
                framework_type = "transformers.js"  # But set dropdown to transformers.js
            elif ("import " in code or "def " in code) and not ("<!DOCTYPE html>" in code or "<html" in code):
                # This looks like Python code but doesn't match Streamlit/Gradio patterns
                # Default to Gradio for Python spaces
                code_lang = "python"
                framework_type = "gradio"
            
            # Return the updates with proper language settings
            return [
                gr.update(value=status, visible=True),
                gr.update(value=code, language=code_lang),  # Use html for transformers.js display
                gr.update(value="", visible=False),  # hide import textbox after submit
                loaded_history,
                history_to_chatbot_messages(loaded_history),
                gr.update(value="Publish", visible=True),
                gr.update(visible=False),  # hide import header
                gr.update(visible=False),  # hide import button
                gr.update(value=framework_type)  # set language dropdown to framework type
            ]
        else:
            # GitHub or HF model → return raw snippet for LLM starting point
            status, code, _ = import_repo_to_app(url)
            loaded_history = [[f"Imported Repo/Model from {url}", code]]
            code_lang = "python"
            framework_type = "gradio"  # Default to gradio for Python code
            lower = (code or "").lower()
            if code.strip().startswith("<!doctype html>") or code.strip().startswith("<html"):
                code_lang = "html"
                framework_type = "html"
            elif "```json" in lower:
                code_lang = "json"
                framework_type = "json"
            return [
                gr.update(value=status, visible=True),
                gr.update(value=code, language=code_lang),
                gr.update(value="", visible=False),  # hide import textbox after submit
                loaded_history,
                history_to_chatbot_messages(loaded_history),
                gr.update(value="Publish", visible=False),
                gr.update(visible=False),  # hide import header
                gr.update(visible=False),  # hide import button
                gr.update(value=framework_type)  # set language dropdown to detected language
            ]

    # Import repo/model handler
    def handle_import_repo(url, framework):
        status, code, preview = import_repo_to_app(url, framework)
        # Heuristically set editor language based on snippet fencing or content
        code_lang = "python"
        lowered = (code or "").lower()
        if code.strip().startswith("<!doctype html>") or code.strip().startswith("<html"):
            code_lang = "html"
        elif "import gradio" in lowered or "from gradio" in lowered:
            code_lang = "python"
        elif "streamlit as st" in lowered or "import streamlit" in lowered:
            code_lang = "python"
        elif "from transformers" in lowered or "import transformers" in lowered:
            code_lang = "python"
        elif "from diffusers" in lowered or "import diffusers" in lowered:
            code_lang = "python"
        return [
            gr.update(value=status, visible=True),
            gr.update(value=code, language=code_lang),
            gr.update(value=""),
            gr.update(value=f"URL: {url}\n\n{status}"),
        ]

    # Event handlers
    def update_code_language(language):
        return gr.update(language=get_gradio_language(language))


    language_dropdown.change(update_code_language, inputs=language_dropdown, outputs=code_output)

    # Toggle single vs multi-file editors for transformers.js and populate when switching
    def toggle_editors(language, code_text):
        if language == "transformers.js":
            files = parse_transformers_js_output(code_text or "")
            # Hide multi-file editors until all files exist; show single code until then
            editors_visible = True if (files.get('index.html') and files.get('index.js') and files.get('style.css')) else False
            return [
                gr.update(visible=not editors_visible),   # code_output shown if editors hidden
                gr.update(visible=editors_visible),       # tjs_group shown only when complete
                gr.update(value=files.get('index.html', '')),
                gr.update(value=files.get('index.js', '')),
                gr.update(value=files.get('style.css', '')),
                # React group hidden
                gr.update(visible=False),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
            ]
        elif language == "react":
            files = parse_react_output(code_text or "")
            # Show react group if we have files, else show single code editor
            editors_visible = True if files else False
            if editors_visible:
                return [
                    gr.update(visible=False),                # code_output hidden
                    gr.update(visible=False),                # tjs_group hidden
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    # React group shown
                    gr.update(visible=editors_visible),      # react_group shown
                    gr.update(value=files.get('Dockerfile', '')),
                    gr.update(value=files.get('package.json', '')),
                    gr.update(value=files.get('next.config.js', '')),
                    gr.update(value=files.get('postcss.config.js', '')),
                    gr.update(value=files.get('tailwind.config.js', '')),
                    gr.update(value=files.get('pages/_app.js', '')),
                    gr.update(value=files.get('pages/index.js', '')),
                    gr.update(value=files.get('components/ChatApp.jsx', '')),
                    gr.update(value=files.get('styles/globals.css', '')),
                ]
            else:
                return [
                    gr.update(visible=True),                 # code_output shown
                    gr.update(visible=False),                # tjs_group hidden
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    # React group hidden
                    gr.update(visible=False),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                ]
        else:
            return [
                gr.update(visible=True),                  # code_output shown
                gr.update(visible=False),                 # tjs_group hidden
                gr.update(),
                gr.update(),
                gr.update(),
                # React group hidden
                gr.update(visible=False),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
            ]

    language_dropdown.change(
        toggle_editors,
        inputs=[language_dropdown, code_output],
        outputs=[code_output, tjs_group, tjs_html_code, tjs_js_code, tjs_css_code, react_group, react_code_dockerfile, react_code_package_json, react_code_next_config, react_code_postcss_config, react_code_tailwind_config, react_code_pages_app, react_code_pages_index, react_code_components, react_code_styles],
    )
    # Toggle Python multi-file editors for Gradio/Streamlit
    def toggle_python_editors(language, code_text):
        if language not in ["gradio", "streamlit"]:
            return [
                gr.update(visible=True),     # code_output
                gr.update(visible=False),    # python_group_2
                gr.update(visible=False),    # python_group_3
                gr.update(visible=False),    # python_group_4
                gr.update(visible=False),    # python_group_5plus
                # All tab and code components get empty updates
                gr.update(), gr.update(), gr.update(), gr.update(),  # 2-file group
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),  # 3-file group
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),  # 4-file group
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update()  # 5-file group
            ]

        files = parse_multi_file_python_output(code_text or "")

        if not isinstance(files, dict) or len(files) <= 1:
            # No multi-file content; keep single editor
            return [
                gr.update(visible=True),     # code_output
                gr.update(visible=False),    # python_group_2
                gr.update(visible=False),    # python_group_3
                gr.update(visible=False),    # python_group_4
                gr.update(visible=False),    # python_group_5plus
                # All tab and code components get empty updates
                gr.update(), gr.update(), gr.update(), gr.update(),  # 2-file group
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),  # 3-file group
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),  # 4-file group
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update()  # 5-file group
            ]

        # We have multi-file Python output: hide single editor, show appropriate group
        # Order: main app first, then others sorted by name
        ordered_paths = []
        main_files = ['app.py', 'streamlit_app.py', 'main.py']
        for main_file in main_files:
            if main_file in files:
                ordered_paths.append(main_file)
                break
        
        for p in sorted(files.keys()):
            if p not in ordered_paths:
                ordered_paths.append(p)

        num_files = len(ordered_paths)
        
        # Hide single editor, show appropriate group based on file count
        updates = [gr.update(visible=False)]  # code_output
        
        if num_files == 2:
            updates.extend([
                gr.update(visible=True),     # python_group_2
                gr.update(visible=False),    # python_group_3
                gr.update(visible=False),    # python_group_4
                gr.update(visible=False),    # python_group_5plus
            ])
            # Populate 2-file group
            path1, path2 = ordered_paths[0], ordered_paths[1]
            updates.extend([
                gr.update(label=path1), gr.update(value=files.get(path1, ''), label=path1, language="python"),
                gr.update(label=path2), gr.update(value=files.get(path2, ''), label=path2, language="python"),
                # Empty updates for unused groups
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
            ])
        elif num_files == 3:
            updates.extend([
                gr.update(visible=False),    # python_group_2
                gr.update(visible=True),     # python_group_3
                gr.update(visible=False),    # python_group_4
                gr.update(visible=False),    # python_group_5plus
            ])
            # Populate 3-file group
            path1, path2, path3 = ordered_paths[0], ordered_paths[1], ordered_paths[2]
            updates.extend([
                # Empty updates for 2-file group
                gr.update(), gr.update(), gr.update(), gr.update(),
                # Populate 3-file group
                gr.update(label=path1), gr.update(value=files.get(path1, ''), label=path1, language="python"),
                gr.update(label=path2), gr.update(value=files.get(path2, ''), label=path2, language="python"),
                gr.update(label=path3), gr.update(value=files.get(path3, ''), label=path3, language="python"),
                # Empty updates for unused groups
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
            ])
        elif num_files == 4:
            updates.extend([
                gr.update(visible=False),    # python_group_2
                gr.update(visible=False),    # python_group_3
                gr.update(visible=True),     # python_group_4
                gr.update(visible=False),    # python_group_5plus
            ])
            # Populate 4-file group
            paths = ordered_paths[:4]
            updates.extend([
                # Empty updates for 2-file and 3-file groups
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                # Populate 4-file group
                gr.update(label=paths[0]), gr.update(value=files.get(paths[0], ''), label=paths[0], language="python"),
                gr.update(label=paths[1]), gr.update(value=files.get(paths[1], ''), label=paths[1], language="python"),
                gr.update(label=paths[2]), gr.update(value=files.get(paths[2], ''), label=paths[2], language="python"),
                gr.update(label=paths[3]), gr.update(value=files.get(paths[3], ''), label=paths[3], language="python"),
                # Empty updates for 5-file group
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
            ])
        else:  # 5+ files
            updates.extend([
                gr.update(visible=False),    # python_group_2
                gr.update(visible=False),    # python_group_3
                gr.update(visible=False),    # python_group_4
                gr.update(visible=True),     # python_group_5plus
            ])
            # Populate 5-file group (show first 5 files)
            paths = ordered_paths[:5]
            updates.extend([
                # Empty updates for 2-file, 3-file, and 4-file groups
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                # Populate 5-file group
                gr.update(label=paths[0]), gr.update(value=files.get(paths[0], ''), label=paths[0], language="python"),
                gr.update(label=paths[1]), gr.update(value=files.get(paths[1], ''), label=paths[1], language="python"),
                gr.update(label=paths[2]), gr.update(value=files.get(paths[2], ''), label=paths[2], language="python"),
                gr.update(label=paths[3]), gr.update(value=files.get(paths[3], ''), label=paths[3], language="python"),
                gr.update(label=paths[4]), gr.update(value=files.get(paths[4], ''), label=paths[4], language="python"),
            ])

        return updates

    language_dropdown.change(
        toggle_python_editors,
        inputs=[language_dropdown, code_output],
        outputs=[
            code_output, python_group_2, python_group_3, python_group_4, python_group_5plus,
            python_tab_2_1, python_code_2_1, python_tab_2_2, python_code_2_2,
            python_tab_3_1, python_code_3_1, python_tab_3_2, python_code_3_2, python_tab_3_3, python_code_3_3,
            python_tab_4_1, python_code_4_1, python_tab_4_2, python_code_4_2, python_tab_4_3, python_code_4_3, python_tab_4_4, python_code_4_4,
            python_tab_5_1, python_code_5_1, python_tab_5_2, python_code_5_2, python_tab_5_3, python_code_5_3, python_tab_5_4, python_code_5_4, python_tab_5_5, python_code_5_5
        ],
    )

    # Static HTML multi-file toggling and population
    def toggle_static_editors(language, code_text):
        # If not static HTML language, ensure single editor visible and all static groups hidden
        if language != "html":
            return [
                gr.update(visible=True),     # code_output
                gr.update(visible=False),    # static_group_2
                gr.update(visible=False),    # static_group_3  
                gr.update(visible=False),    # static_group_4
                gr.update(visible=False),    # static_group_5plus
                # All tab and code components get empty updates (tab, code, tab, code, ...)
                gr.update(), gr.update(), gr.update(), gr.update(),  # 2-file group
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),  # 3-file group
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),  # 4-file group
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update()  # 5-file group
            ]

        # Parse multi-file output first
        original_files = parse_multipage_html_output(code_text or "")
        
        # Check if we actually have multi-file content BEFORE validation
        # (validate_and_autofix_files can create additional files from single-file HTML)
        if not isinstance(original_files, dict) or len(original_files) <= 1:
            # No genuine multi-file content; keep single editor
            return [
                gr.update(visible=True),     # code_output
                gr.update(visible=False),    # static_group_2
                gr.update(visible=False),    # static_group_3  
                gr.update(visible=False),    # static_group_4
                gr.update(visible=False),    # static_group_5plus
                # All tab and code components get empty updates (tab, code, tab, code, ...)
                gr.update(), gr.update(), gr.update(), gr.update(),  # 2-file group
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),  # 3-file group
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),  # 4-file group
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update()  # 5-file group
            ]
        
        # We have genuine multi-file content - now validate and proceed with multi-file display
        files = validate_and_autofix_files(original_files)

        # We have multi-file static output: hide single editor, show appropriate static group
        # Order: index.html first, then others sorted by path
        ordered_paths = []
        if 'index.html' in files:
            ordered_paths.append('index.html')
        for p in sorted(files.keys()):
            if p == 'index.html':
                continue
            ordered_paths.append(p)

        # Map extension to language
        def _lang_for(path: str):
            p = (path or '').lower()
            if p.endswith('.html'):
                return 'html'
            if p.endswith('.css'):
                return 'css'
            if p.endswith('.js'):
                return 'javascript'
            if p.endswith('.json'):
                return 'json'
            if p.endswith('.md') or p.endswith('.markdown'):
                return 'markdown'
            return 'html'

        num_files = len(ordered_paths)
        
        # TEMPORARY FIX: For now, always keep single editor visible for HTML multi-file
        # This ensures code is always visible while we debug the multi-file editors
        # TODO: Remove this once multi-file editors are working properly
        updates = [
            gr.update(visible=True),     # code_output - keep visible
            gr.update(visible=False),    # static_group_2 - hide multi-file editors for now
            gr.update(visible=False),    # static_group_3
            gr.update(visible=False),    # static_group_4
            gr.update(visible=False),    # static_group_5plus
        ]
        
        # Add empty updates for all the tab and code components
        updates.extend([
            # All tab and code components get empty updates (tab, code, tab, code, ...)
            gr.update(), gr.update(), gr.update(), gr.update(),  # 2-file group
            gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),  # 3-file group
            gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),  # 4-file group
            gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update()  # 5-file group
        ])
        
        return updates

    # Respond to language change to show/hide static multi-file editors appropriately
    language_dropdown.change(
        toggle_static_editors,
        inputs=[language_dropdown, code_output],
        outputs=[
            code_output, 
            static_group_2, static_group_3, static_group_4, static_group_5plus,
            static_tab_2_1, static_code_2_1, static_tab_2_2, static_code_2_2,
            static_tab_3_1, static_code_3_1, static_tab_3_2, static_code_3_2, static_tab_3_3, static_code_3_3,
            static_tab_4_1, static_code_4_1, static_tab_4_2, static_code_4_2, static_tab_4_3, static_code_4_3, static_tab_4_4, static_code_4_4,
            static_tab_5_1, static_code_5_1, static_tab_5_2, static_code_5_2, static_tab_5_3, static_code_5_3, static_tab_5_4, static_code_5_4, static_tab_5_5, static_code_5_5,
        ],
    )

    def sync_tjs_from_code(code_text, language):
        if language != "transformers.js":
            return [gr.update(), gr.update(), gr.update(), gr.update()]
        files = parse_transformers_js_output(code_text or "")
        # Only reveal the multi-file editors when all three files are present
        editors_visible = True if (files.get('index.html') and files.get('index.js') and files.get('style.css')) else None
        return [
            gr.update(value=files.get('index.html', '')),
            gr.update(value=files.get('index.js', '')),
            gr.update(value=files.get('style.css', '')),
            gr.update(visible=editors_visible) if editors_visible is not None else gr.update(),
        ]

    # Keep multi-file editors in sync when code_output changes and language is transformers.js
    code_output.change(
        sync_tjs_from_code,
        inputs=[code_output, language_dropdown],
        outputs=[tjs_html_code, tjs_js_code, tjs_css_code, tjs_group],
    )

    # Preview functions removed - replaced with deployment messaging
    # The following functions are no longer used as preview has been removed:
    # - preview_logic: replaced with deployment messages
    # - preview_from_tjs_editors: replaced with deployment messages
    # - send_to_sandbox: still used in some places but could be removed in future cleanup

    # Show deployment message for transformers.js editors
    def show_tjs_deployment_message(*args):
        return """
        <div style='padding: 1.5em; text-align: center; background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); color: white; border-radius: 10px;'>
            <h3 style='margin-top: 0; color: white;'>🚀 Transformers.js App Ready!</h3>
            <p style='margin: 0.5em 0; opacity: 0.9;'>Your multi-file Transformers.js application is ready for deployment.</p>
            <p style='margin: 0.5em 0; font-weight: bold;'>👉 Use the Deploy button in the sidebar to publish your app!</p>
        </div>
        """
    

    def show_deploy_components(*args):
        return gr.Button(visible=True)

    def hide_deploy_components(*args):
        return gr.Button(visible=True)
    
    # Show textbox when import button is clicked
    def toggle_import_textbox(url_visible):
        # If textbox is already visible and has content, proceed with import
        # Otherwise, just show the textbox
        return gr.update(visible=True)
    
    load_project_btn.click(
        fn=toggle_import_textbox,
        inputs=[load_project_url],
        outputs=[load_project_url]
    ).then(
        handle_import_project,
        inputs=[load_project_url],
        outputs=[
            load_project_status,
            code_output,
            load_project_url,
            history,
            history_output,
            deploy_btn,
            import_header_md,
            load_project_btn,
            language_dropdown,
        ],
    )





    def begin_generation_ui():
        # Collapse the sidebar when generation starts; keep status hidden
        return [gr.update(open=False), gr.update(visible=False)]

    def end_generation_ui():
        # Open sidebar after generation; hide the status
        return [gr.update(open=True), gr.update(visible=False)]

    def generation_code_wrapper(inp, sett, hist, model, lang, prov, profile: gr.OAuthProfile | None = None, token: gr.OAuthToken | None = None):
        """Wrapper to call generation_code without image input"""
        yield from generation_code(inp, None, sett, hist, model, lang, prov, profile, token)

    btn.click(
        begin_generation_ui,
        inputs=None,
        outputs=[sidebar, generating_status],
        show_progress="hidden",
    ).then(
        generation_code_wrapper,
        inputs=[input, setting, history, current_model, language_dropdown, provider_state],
        outputs=[code_output, history, history_output]
    ).then(
        end_generation_ui,
        inputs=None,
        outputs=[sidebar, generating_status]
    ).then(
        # After generation, toggle editors for transformers.js and populate
        toggle_editors,
        inputs=[language_dropdown, code_output],
        outputs=[code_output, tjs_group, tjs_html_code, tjs_js_code, tjs_css_code, react_group, react_code_dockerfile, react_code_package_json, react_code_next_config, react_code_postcss_config, react_code_tailwind_config, react_code_pages_app, react_code_pages_index, react_code_components, react_code_styles]
    ).then(
        # After generation, toggle static multi-file editors for HTML
        toggle_static_editors,
        inputs=[language_dropdown, code_output],
        outputs=[
            code_output, 
            static_group_2, static_group_3, static_group_4, static_group_5plus,
            static_tab_2_1, static_code_2_1, static_tab_2_2, static_code_2_2,
            static_tab_3_1, static_code_3_1, static_tab_3_2, static_code_3_2, static_tab_3_3, static_code_3_3,
            static_tab_4_1, static_code_4_1, static_tab_4_2, static_code_4_2, static_tab_4_3, static_code_4_3, static_tab_4_4, static_code_4_4,
            static_tab_5_1, static_code_5_1, static_tab_5_2, static_code_5_2, static_tab_5_3, static_code_5_3, static_tab_5_4, static_code_5_4, static_tab_5_5, static_code_5_5,
        ]
    ).then(
        # After generation, toggle Python multi-file editors for Gradio/Streamlit
        toggle_python_editors,
        inputs=[language_dropdown, code_output],
        outputs=[
            code_output, python_group_2, python_group_3, python_group_4, python_group_5plus,
            python_tab_2_1, python_code_2_1, python_tab_2_2, python_code_2_2,
            python_tab_3_1, python_code_3_1, python_tab_3_2, python_code_3_2, python_tab_3_3, python_code_3_3,
            python_tab_4_1, python_code_4_1, python_tab_4_2, python_code_4_2, python_tab_4_3, python_code_4_3, python_tab_4_4, python_code_4_4,
            python_tab_5_1, python_code_5_1, python_tab_5_2, python_code_5_2, python_tab_5_3, python_code_5_3, python_tab_5_4, python_code_5_4, python_tab_5_5, python_code_5_5
        ]
    ).then(
        show_deploy_components,
        None,
        [deploy_btn]
    )

    # Pressing Enter in the main input should trigger generation and collapse the sidebar
    input.submit(
        begin_generation_ui,
        inputs=None,
        outputs=[sidebar, generating_status],
        show_progress="hidden",
    ).then(
        generation_code_wrapper,
        inputs=[input, setting, history, current_model, language_dropdown, provider_state],
        outputs=[code_output, history, history_output]
    ).then(
        end_generation_ui,
        inputs=None,
        outputs=[sidebar, generating_status]
    ).then(
        # After generation, toggle editors for transformers.js and populate
        toggle_editors,
        inputs=[language_dropdown, code_output],
        outputs=[code_output, tjs_group, tjs_html_code, tjs_js_code, tjs_css_code, react_group, react_code_dockerfile, react_code_package_json, react_code_next_config, react_code_postcss_config, react_code_tailwind_config, react_code_pages_app, react_code_pages_index, react_code_components, react_code_styles]
    ).then(
        # After generation, toggle static multi-file editors for HTML
        toggle_static_editors,
        inputs=[language_dropdown, code_output],
        outputs=[
            code_output, 
            static_group_2, static_group_3, static_group_4, static_group_5plus,
            static_tab_2_1, static_code_2_1, static_tab_2_2, static_code_2_2,
            static_tab_3_1, static_code_3_1, static_tab_3_2, static_code_3_2, static_tab_3_3, static_code_3_3,
            static_tab_4_1, static_code_4_1, static_tab_4_2, static_code_4_2, static_tab_4_3, static_code_4_3, static_tab_4_4, static_code_4_4,
            static_tab_5_1, static_code_5_1, static_tab_5_2, static_code_5_2, static_tab_5_3, static_code_5_3, static_tab_5_4, static_code_5_4, static_tab_5_5, static_code_5_5,
        ]
    ).then(
        # After generation, toggle Python multi-file editors for Gradio/Streamlit
        toggle_python_editors,
        inputs=[language_dropdown, code_output],
        outputs=[
            code_output, python_group_2, python_group_3, python_group_4, python_group_5plus,
            python_tab_2_1, python_code_2_1, python_tab_2_2, python_code_2_2,
            python_tab_3_1, python_code_3_1, python_tab_3_2, python_code_3_2, python_tab_3_3, python_code_3_3,
            python_tab_4_1, python_code_4_1, python_tab_4_2, python_code_4_2, python_tab_4_3, python_code_4_3, python_tab_4_4, python_code_4_4,
            python_tab_5_1, python_code_5_1, python_tab_5_2, python_code_5_2, python_tab_5_3, python_code_5_3, python_tab_5_4, python_code_5_4, python_tab_5_5, python_code_5_5
        ]
    ).then(
        show_deploy_components,
        None,
        [deploy_btn]
    )

    # --- Chat-based sidebar controller logic ---
    def _find_model_by_name(name: str):
        for m in AVAILABLE_MODELS:
            if m["name"].lower() == name.lower():
                return m
        return None

    def _extract_url(text: str) -> str | None:
        import re
        match = re.search(r"https?://[^\s]+", text or "")
        return match.group(0) if match else None


    # Show deployment message when code or language changes
    def show_deployment_message(code, language, *args):
        if not code or not code.strip():
            return "<div style='padding:1em;color:#888;text-align:center;'>Generate some code to see deployment options.</div>"
        return f"""
        <div style='padding: 1.5em; text-align: center; background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; border-radius: 10px;'>
            <h3 style='margin-top: 0; color: white;'>Ready to Deploy!</h3>
            <p style='margin: 0.5em 0; opacity: 0.9;'>Your {language.upper()} code is ready for deployment.</p>
            <p style='margin: 0.5em 0; font-weight: bold;'>👉 Use the Deploy button in the sidebar to publish your app!</p>
        </div>
        """
    
    clear_btn.click(clear_history, outputs=[history, history_output])
    clear_btn.click(hide_deploy_components, None, [deploy_btn])
    # Reset button text when clearing
    clear_btn.click(
        lambda: gr.update(value="Publish"),
        outputs=[deploy_btn]
    )

    # Deploy to Spaces logic
    
    def generate_random_app_name():
        """Generate a random app name that's unlikely to clash with existing apps"""
        import random
        import string
        
        # Common app prefixes
        prefixes = ["my", "cool", "awesome", "smart", "quick", "super", "mini", "auto", "fast", "easy"]
        # Common app suffixes  
        suffixes = ["app", "tool", "hub", "space", "demo", "ai", "gen", "bot", "lab", "studio"]
        # Random adjectives
        adjectives = ["blue", "red", "green", "bright", "dark", "light", "swift", "bold", "clean", "fresh"]
        
        # Generate different patterns
        patterns = [
            lambda: f"{random.choice(prefixes)}-{random.choice(suffixes)}-{random.randint(100, 999)}",
            lambda: f"{random.choice(adjectives)}-{random.choice(suffixes)}-{random.randint(10, 99)}",
            lambda: f"{random.choice(prefixes)}-{random.choice(adjectives)}-{random.choice(suffixes)}",
            lambda: f"app-{''.join(random.choices(string.ascii_lowercase, k=6))}-{random.randint(10, 99)}",
            lambda: f"{random.choice(suffixes)}-{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}"
        ]
        
        return random.choice(patterns)()

    def deploy_with_history_tracking(
        code, 
        language, 
        history,
        profile: gr.OAuthProfile | None = None, 
        token: gr.OAuthToken | None = None
    ):
        """Wrapper function that handles history tracking for deployments"""
        # Check if we have a previously deployed space in the history
        username = profile.username if profile else None
        existing_space = None
        
        # Look for previous deployment or imported space in history
        if history and username:
            for user_msg, assistant_msg in history:
                if assistant_msg and "✅ Deployed!" in assistant_msg:
                    import re
                    # Look for space URL pattern
                    match = re.search(r'huggingface\.co/spaces/([^/\s\)]+/[^/\s\)]+)', assistant_msg)
                    if match:
                        existing_space = match.group(1)
                        break
                elif assistant_msg and "✅ Updated!" in assistant_msg:
                    import re
                    # Look for space URL pattern
                    match = re.search(r'huggingface\.co/spaces/([^/\s\)]+/[^/\s\)]+)', assistant_msg)
                    if match:
                        existing_space = match.group(1)
                        break
                elif user_msg and user_msg.startswith("Imported Space from"):
                    import re
                    # Extract space name from import message
                    match = re.search(r'huggingface\.co/spaces/([^/\s\)]+/[^/\s\)]+)', user_msg)
                    if match:
                        imported_space = match.group(1)
                        # Only use imported space if user owns it (can update it)
                        if imported_space.startswith(f"{username}/"):
                            existing_space = imported_space
                            break
                        # If user doesn't own the imported space, we'll create a new one
                        # (existing_space remains None, triggering new deployment)
        
        # Call the original deploy function
        status = deploy_to_user_space_original(code, language, existing_space, profile, token)
        
        # Update history if deployment was successful
        updated_history = history
        if isinstance(status, dict) and "value" in status and "✅" in status["value"]:
            action_type = "Deploy" if "Deployed!" in status["value"] else "Update"
            if existing_space:
                updated_history = history + [[f"{action_type} {language} app to {existing_space}", status["value"]]]
            else:
                updated_history = history + [[f"{action_type} {language} app", status["value"]]]
        
        return [status, updated_history]

    def deploy_to_user_space_original(
        code, 
        language, 
        existing_space_name=None,  # Pass existing space name if updating
        profile: gr.OAuthProfile | None = None, 
        token: gr.OAuthToken | None = None
    ):
        import shutil
        if not code or not code.strip():
            return gr.update(value="No code to deploy.", visible=True)
        if profile is None or token is None:
            return gr.update(value="Please log in with your Hugging Face account to deploy to your own Space. Otherwise, use the default deploy (opens in new tab).", visible=True)
        
        # Check if token has write permissions
        if not token.token or token.token == "hf_":
            return gr.update(value="Error: Invalid token. Please log in again with your Hugging Face account to get a valid write token.", visible=True)
        
        # Determine if this is an update or new deployment
        username = profile.username
        if existing_space_name and existing_space_name.startswith(f"{username}/"):
            # This is an update to existing space
            repo_id = existing_space_name
            space_name = existing_space_name.split('/')[-1]
            is_update = True
        else:
            # Generate a random space name for new deployment
            space_name = generate_random_app_name()
            repo_id = f"{username}/{space_name}"
            is_update = False
        # Map language to HF SDK slug
        language_to_sdk_map = {
            "gradio": "gradio",
            "streamlit": "docker",  # Use 'docker' for Streamlit Spaces
            "react": "docker",  # Use 'docker' for React/Next.js Spaces
            "html": "static",
            "transformers.js": "static",  # Transformers.js uses static SDK
            "comfyui": "static"  # ComfyUI uses static SDK
        }
        sdk = language_to_sdk_map.get(language, "gradio")
        
        # Create API client with user's token for proper authentication
        api = HfApi(token=token.token)
        # Only create the repo for new spaces (not updates) and non-Transformers.js, non-Streamlit SDKs
        if not is_update and sdk != "docker" and language not in ["transformers.js"]:
            try:
                api.create_repo(
                    repo_id=repo_id,  # e.g. username/space_name
                    repo_type="space",
                    space_sdk=sdk,  # Use selected SDK
                    exist_ok=True  # Don't error if it already exists
                )
            except Exception as e:
                return gr.update(value=f"Error creating Space: {e}", visible=True)
        # Streamlit/React/docker logic
        if sdk == "docker" and language in ["streamlit", "react"]:
            try:
                # For new spaces, create a fresh Docker-based space
                if not is_update:
                    # Use create_repo to create a new Docker space
                    from huggingface_hub import create_repo
                    
                    if language == "react":
                        # Create a new React Docker space with docker SDK
                        created_repo = create_repo(
                            repo_id=repo_id,
                            repo_type="space",
                            space_sdk="docker",
                            token=token.token,
                            exist_ok=True
                        )
                    else:
                        # Create a new Streamlit Docker space
                        created_repo = create_repo(
                            repo_id=repo_id,
                            repo_type="space",
                            space_sdk="docker",
                            token=token.token,
                            exist_ok=True
                        )
                
                # Handle React or Streamlit deployment
                if language == "react":
                    # Parse React/Next.js files
                    files = parse_react_output(code)
                    if not files:
                        return gr.update(value="Error: Could not parse React output. Please regenerate the code.", visible=True)
                    
                    # Upload React files
                    import tempfile
                    import time
                    
                    for file_name, file_content in files.items():
                        if not file_content:
                            continue
                            
                        success = False
                        last_error = None
                        max_attempts = 3
                        
                        for attempt in range(max_attempts):
                            try:
                                with tempfile.NamedTemporaryFile("w", suffix=f".{file_name.split('.')[-1]}", delete=False) as f:
                                    f.write(file_content)
                                    temp_path = f.name
                                
                                api.upload_file(
                                    path_or_fileobj=temp_path,
                                    path_in_repo=file_name,
                                    repo_id=repo_id,
                                    repo_type="space"
                                )
                                success = True
                                break
                                
                            except Exception as e:
                                last_error = e
                                error_msg = str(e)
                                if "403 Forbidden" in error_msg and "write token" in error_msg:
                                    return gr.update(value=f"Error: Permission denied. Please ensure you have write access to {repo_id} and your token has the correct permissions.", visible=True)
                                
                                if attempt < max_attempts - 1:
                                    time.sleep(2)
                            finally:
                                import os
                                if 'temp_path' in locals():
                                    os.unlink(temp_path)
                        
                        if not success:
                            return gr.update(value=f"Error uploading {file_name}: {last_error}", visible=True)
                    
                    # Add anycoder tag and app_port to existing README
                    add_anycoder_tag_to_readme(api, repo_id, app_port=7860)
                    
                    space_url = f"https://huggingface.co/spaces/{repo_id}"
                    action_text = "Updated" if is_update else "Deployed"
                    return gr.update(value=f"✅ {action_text}! [Open your React Space here]({space_url})", visible=True)
                
                # Streamlit logic
                # Generate requirements.txt for Streamlit apps and upload only if needed
                import_statements = extract_import_statements(code)
                requirements_content = generate_requirements_txt_with_llm(import_statements)
                
                import tempfile
                
                # Check if we need to upload requirements.txt
                should_upload_requirements = True
                if is_update:
                    try:
                        # Try to get existing requirements.txt content
                        existing_requirements = api.hf_hub_download(
                            repo_id=repo_id,
                            filename="requirements.txt",
                            repo_type="space"
                        )
                        with open(existing_requirements, 'r') as f:
                            existing_content = f.read().strip()
                        
                        # Compare with new content
                        if existing_content == requirements_content.strip():
                            should_upload_requirements = False
                            
                    except Exception:
                        # File doesn't exist or can't be accessed, so we should upload
                        should_upload_requirements = True
                
                # Upload requirements.txt only if needed
                if should_upload_requirements:
                    try:
                        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
                            f.write(requirements_content)
                            requirements_temp_path = f.name
                        
                        api.upload_file(
                            path_or_fileobj=requirements_temp_path,
                            path_in_repo="requirements.txt",
                            repo_id=repo_id,
                            repo_type="space"
                        )
                    except Exception as e:
                        error_msg = str(e)
                        if "403 Forbidden" in error_msg and "write token" in error_msg:
                            return gr.update(value=f"Error uploading requirements.txt: Permission denied. Please ensure you have write access to {repo_id} and your token has the correct permissions.", visible=True)
                        else:
                            return gr.update(value=f"Error uploading requirements.txt: {e}", visible=True)
                    finally:
                        import os
                        if 'requirements_temp_path' in locals():
                            os.unlink(requirements_temp_path)
                
                # Add anycoder tag to existing README
                add_anycoder_tag_to_readme(api, repo_id)
                
                # Upload the user's code to src/streamlit_app.py (for both new and existing spaces)
                with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
                    f.write(code)
                    temp_path = f.name
                
                try:
                    api.upload_file(
                        path_or_fileobj=temp_path,
                        path_in_repo="src/streamlit_app.py",
                        repo_id=repo_id,
                        repo_type="space"
                    )
                    space_url = f"https://huggingface.co/spaces/{repo_id}"
                    action_text = "Updated" if is_update else "Deployed"
                    return gr.update(value=f"✅ {action_text}! [Open your Space here]({space_url})", visible=True)
                except Exception as e:
                    error_msg = str(e)
                    if "403 Forbidden" in error_msg and "write token" in error_msg:
                        return gr.update(value=f"Error: Permission denied. Please ensure you have write access to {repo_id} and your token has the correct permissions.", visible=True)
                    else:
                        return gr.update(value=f"Error uploading Streamlit app: {e}", visible=True)
                finally:
                    import os
                    os.unlink(temp_path)
                    
            except Exception as e:
                error_prefix = "Error duplicating Streamlit space" if not is_update else "Error updating Streamlit space"
                return gr.update(value=f"{error_prefix}: {e}", visible=True)
        # Transformers.js logic
        elif language == "transformers.js":
            try:
                # For new spaces, duplicate the template. For updates, just verify access.
                if not is_update:
                    # Use duplicate_space to create a transformers.js template space
                    from huggingface_hub import duplicate_space
                    
                    # Duplicate the transformers.js template space
                    duplicated_repo = duplicate_space(
                        from_id="static-templates/transformers.js",
                        to_id=space_name.strip(),
                        token=token.token,
                        exist_ok=True
                    )
                    print("Duplicated repo result:", duplicated_repo, type(duplicated_repo))
                else:
                    # For updates, verify we can access the existing space
                    try:
                        space_info = api.space_info(repo_id)
                        if not space_info:
                            return gr.update(value=f"Error: Could not access space {repo_id} for update.", visible=True)
                    except Exception as e:
                        return gr.update(value=f"Error: Cannot update space {repo_id}. {str(e)}", visible=True)
                # Parse the code parameter which should contain the formatted transformers.js output
                files = parse_transformers_js_output(code)
                
                if not files['index.html'] or not files['index.js'] or not files['style.css']:
                    return gr.update(value="Error: Could not parse transformers.js output. Please regenerate the code.", visible=True)
                
                # Upload the three files to the space (with retry logic for reliability)
                import tempfile
                import time
                
                # Define files to upload
                files_to_upload = [
                    ("index.html", files['index.html']),
                    ("index.js", files['index.js']),
                    ("style.css", files['style.css'])
                ]
                
                # Upload each file with retry logic (similar to static HTML pattern)
                max_attempts = 3
                for file_name, file_content in files_to_upload:
                    success = False
                    last_error = None
                    
                    for attempt in range(max_attempts):
                        try:
                            with tempfile.NamedTemporaryFile("w", suffix=f".{file_name.split('.')[-1]}", delete=False) as f:
                                f.write(file_content)
                                temp_path = f.name
                            
                            api.upload_file(
                                path_or_fileobj=temp_path,
                                path_in_repo=file_name,
                                repo_id=repo_id,
                                repo_type="space"
                            )
                            success = True
                            break
                            
                        except Exception as e:
                            last_error = e
                            error_msg = str(e)
                            if "403 Forbidden" in error_msg and "write token" in error_msg:
                                # Permission errors won't be fixed by retrying
                                return gr.update(value=f"Error: Permission denied. Please ensure you have write access to {repo_id} and your token has the correct permissions.", visible=True)
                            
                            if attempt < max_attempts - 1:  # Not the last attempt
                                time.sleep(2)  # Wait before retrying
                        finally:
                            import os
                            if 'temp_path' in locals():
                                os.unlink(temp_path)
                    
                    if not success:
                        return gr.update(value=f"Error uploading {file_name}: {last_error}", visible=True)
                
                # Add anycoder tag to existing README (for both new and update)
                add_anycoder_tag_to_readme(api, repo_id)
                
                # For updates, trigger a space restart to ensure changes take effect
                if is_update:
                    try:
                        api.restart_space(repo_id=repo_id)
                    except Exception as restart_error:
                        # Don't fail the deployment if restart fails, just log it
                        print(f"Note: Could not restart space after update: {restart_error}")
                
                space_url = f"https://huggingface.co/spaces/{repo_id}"
                action_text = "Updated" if is_update else "Deployed"
                return gr.update(value=f"✅ {action_text}! [Open your Transformers.js Space here]({space_url})", visible=True)
                    
            except Exception as e:
                # Handle potential RepoUrl object errors
                error_msg = str(e)
                if "'url'" in error_msg or "RepoUrl" in error_msg:
                    # For RepoUrl object issues, check if the space was actually created successfully
                    try:
                        # Check if space exists by trying to access it
                        space_url = f"https://huggingface.co/spaces/{repo_id}"
                        test_api = HfApi(token=token.token)
                        space_exists = test_api.space_info(repo_id)
                        
                        if space_exists and not is_update:
                            # Space was created successfully despite the RepoUrl error
                            return gr.update(value=f"✅ Deployed! Space was created successfully despite a technical error. [Open your Transformers.js Space here]({space_url})", visible=True)
                        elif space_exists and is_update:
                            # Space was updated successfully despite the RepoUrl error  
                            return gr.update(value=f"✅ Updated! Space was updated successfully despite a technical error. [Open your Transformers.js Space here]({space_url})", visible=True)
                        else:
                            # Space doesn't exist, real error
                            return gr.update(value=f"Error: Could not create/update space. Please try again manually at https://huggingface.co/new-space", visible=True)
                    except:
                        # Fallback to informative error with link
                        repo_url = f"https://huggingface.co/spaces/{repo_id}"
                        return gr.update(value=f"Error: Could not properly handle space creation response. Space may have been created successfully. Check: {repo_url}", visible=True)
                
                # General error handling for both creation and updates
                action_verb = "updating" if is_update else "duplicating"
                return gr.update(value=f"Error {action_verb} Transformers.js space: {error_msg}", visible=True)
        # Other SDKs (existing logic)
        if sdk == "static":
            import time
            
            # Add anycoder tag to existing README (after repo creation)
            add_anycoder_tag_to_readme(api, repo_id)
            
            # Detect whether the HTML output is multi-file (=== filename === blocks)
            files = {}
            try:
                files = parse_multipage_html_output(code)
                files = validate_and_autofix_files(files)
            except Exception:
                files = {}
            
            # If we have multiple files (or at least a parsed index.html), upload the whole folder
            if isinstance(files, dict) and files.get('index.html'):
                import tempfile
                import os
                
                try:
                    with tempfile.TemporaryDirectory() as tmpdir:
                        # Write each file preserving subdirectories if any
                        for rel_path, content in files.items():
                            safe_rel_path = rel_path.strip().lstrip('/')
                            abs_path = os.path.join(tmpdir, safe_rel_path)
                            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                            with open(abs_path, 'w') as fh:
                                fh.write(content)
                        
                        # Upload the folder in a single commit
                        api.upload_folder(
                            folder_path=tmpdir,
                            repo_id=repo_id,
                            repo_type="space"
                        )
                    space_url = f"https://huggingface.co/spaces/{repo_id}"
                    action_text = "Updated" if is_update else "Deployed"
                    return gr.update(value=f"✅ {action_text}! [Open your Space here]({space_url})", visible=True)
                except Exception as e:
                    error_msg = str(e)
                    if "403 Forbidden" in error_msg and "write token" in error_msg:
                        return gr.update(value=f"Error: Permission denied. Please ensure you have write access to {repo_id} and your token has the correct permissions.", visible=True)
                    else:
                        return gr.update(value=f"Error uploading static app folder: {e}", visible=True)
            
            # Fallback: single-file static HTML (upload index.html only)
            file_name = "index.html"
            
            # Special handling for ComfyUI: prettify JSON and wrap in HTML
            if language == "comfyui":
                print("[Deploy] Converting ComfyUI JSON to prettified HTML display")
                code = prettify_comfyui_json_for_html(code)
            
            max_attempts = 3
            for attempt in range(max_attempts):
                import tempfile
                with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
                    f.write(code)
                    temp_path = f.name
                try:
                    api.upload_file(
                        path_or_fileobj=temp_path,
                        path_in_repo=file_name,
                        repo_id=repo_id,
                        repo_type="space"
                    )
                    space_url = f"https://huggingface.co/spaces/{repo_id}"
                    action_text = "Updated" if is_update else "Deployed"
                    return gr.update(value=f"✅ {action_text}! [Open your Space here]({space_url})", visible=True)
                except Exception as e:
                    error_msg = str(e)
                    if "403 Forbidden" in error_msg and "write token" in error_msg:
                        return gr.update(value=f"Error: Permission denied. Please ensure you have write access to {repo_id} and your token has the correct permissions.", visible=True)
                    elif attempt < max_attempts - 1:
                        time.sleep(2)
                    else:
                        return gr.update(value=f"Error uploading file after {max_attempts} attempts: {e}. Please check your permissions and try again.", visible=True)
                finally:
                    import os
                    os.unlink(temp_path)
        else:
            # Generate requirements.txt for Gradio apps and upload only if needed
            import_statements = extract_import_statements(code)
            requirements_content = generate_requirements_txt_with_llm(import_statements)
            
            import tempfile
            
            # Check if we need to upload requirements.txt
            should_upload_requirements = True
            if is_update:
                try:
                    # Try to get existing requirements.txt content
                    existing_requirements = api.hf_hub_download(
                        repo_id=repo_id,
                        filename="requirements.txt",
                        repo_type="space"
                    )
                    with open(existing_requirements, 'r') as f:
                        existing_content = f.read().strip()
                    
                    # Compare with new content
                    if existing_content == requirements_content.strip():
                        should_upload_requirements = False
                        
                except Exception:
                    # File doesn't exist or can't be accessed, so we should upload
                    should_upload_requirements = True
            
            # Note: requirements.txt upload is now handled by the multi-file commit logic below
            # This ensures all files are committed atomically in a single operation
            
            # Add anycoder tag to existing README
            add_anycoder_tag_to_readme(api, repo_id)
            
            # Check if code contains multi-file format
            if ('=== app.py ===' in code or '=== requirements.txt ===' in code):
                # Parse multi-file format and upload each file separately
                files = parse_multi_file_python_output(code)
                if files:
                    # Ensure requirements.txt is present - auto-generate if missing
                    if 'app.py' in files and 'requirements.txt' not in files:
                        import_statements = extract_import_statements(files['app.py'])
                        requirements_content = generate_requirements_txt_with_llm(import_statements)
                        files['requirements.txt'] = requirements_content
                    try:
                        from huggingface_hub import CommitOperationAdd
                        operations = []
                        temp_files = []
                        
                        # Create CommitOperation for each file
                        for filename, content in files.items():
                            # Clean content to ensure no stray backticks are deployed
                            cleaned_content = content
                            if filename.endswith('.txt') or filename.endswith('.py'):
                                # Additional safety: remove any standalone backtick lines
                                lines = cleaned_content.split('\n')
                                clean_lines = []
                                for line in lines:
                                    stripped = line.strip()
                                    # Skip lines that are just backticks
                                    if stripped == '```' or (stripped.startswith('```') and len(stripped) <= 10):
                                        continue
                                    clean_lines.append(line)
                                cleaned_content = '\n'.join(clean_lines)
                            
                            # Create temporary file
                            with tempfile.NamedTemporaryFile("w", suffix=f".{filename.split('.')[-1]}", delete=False) as f:
                                f.write(cleaned_content)
                                temp_path = f.name
                                temp_files.append(temp_path)
                            
                            # Add to operations
                            operations.append(CommitOperationAdd(
                                path_in_repo=filename,
                                path_or_fileobj=temp_path
                            ))
                        
                        # Commit all files at once
                        api.create_commit(
                            repo_id=repo_id,
                            operations=operations,
                            commit_message=f"{'Update' if is_update else 'Deploy'} Gradio app with multiple files",
                            repo_type="space"
                        )
                        
                        # Clean up temp files
                        for temp_path in temp_files:
                            try:
                                os.unlink(temp_path)
                            except Exception:
                                pass
                        
                        space_url = f"https://huggingface.co/spaces/{repo_id}"
                        action_text = "Updated" if is_update else "Deployed"
                        return gr.update(value=f"✅ {action_text}! [Open your Space here]({space_url})", visible=True)
                        
                    except Exception as e:
                        # Clean up temp files on error
                        for temp_path in temp_files:
                            try:
                                os.unlink(temp_path)
                            except Exception:
                                pass
                        
                        error_msg = str(e)
                        if "403 Forbidden" in error_msg and "write token" in error_msg:
                            return gr.update(value=f"Error: Permission denied. Please ensure you have write access to {repo_id} and your token has the correct permissions.", visible=True)
                        else:
                            return gr.update(value=f"Error uploading multi-file app: {e}", visible=True)
                else:
                    # Fallback to single file if parsing failed
                    pass
            
            # Single file upload (fallback or non-multi-file format)
            file_name = "app.py"
            with tempfile.NamedTemporaryFile("w", suffix=f".{file_name.split('.')[-1]}", delete=False) as f:
                f.write(code)
                temp_path = f.name
            try:
                api.upload_file(
                    path_or_fileobj=temp_path,
                    path_in_repo=file_name,
                    repo_id=repo_id,
                    repo_type="space"
                )
                space_url = f"https://huggingface.co/spaces/{repo_id}"
                action_text = "Updated" if is_update else "Deployed"
                return gr.update(value=f"✅ {action_text}! [Open your Space here]({space_url})", visible=True)
            except Exception as e:
                error_msg = str(e)
                if "403 Forbidden" in error_msg and "write token" in error_msg:
                    return gr.update(value=f"Error: Permission denied. Please ensure you have write access to {repo_id} and your token has the correct permissions.", visible=True)
                else:
                    return gr.update(value=f"Error uploading file: {e}", visible=True)
            finally:
                import os
                os.unlink(temp_path)

    # Connect the deploy button to the new function
    def gather_code_for_deploy(code_text, language, html_part, js_part, css_part):
        # When transformers.js is selected, ensure multi-file editors are used; otherwise, return single code
        if language == "transformers.js":
            # Join into a combined display string for auditing; actual deploy reads editor values directly
            files = {
                'index.html': html_part or '',
                'index.js': js_part or '',
                'style.css': css_part or '',
            }
            if files['index.html'] and files['index.js'] and files['style.css']:
                return format_transformers_js_output(files)
        return code_text
    deploy_btn.click(
        gather_code_for_deploy,
        inputs=[code_output, language_dropdown, tjs_html_code, tjs_js_code, tjs_css_code],
        outputs=[code_output],
        queue=False,
    ).then(
        deploy_with_history_tracking,
        inputs=[code_output, language_dropdown, history],
        outputs=[deploy_status, history]
    )
    # Keep the old deploy method as fallback (if not logged in, user can still use the old method)
    # Optionally, you can keep the old deploy_btn.click for the default method as a secondary button.
    
    # Handle authentication state updates
    # The LoginButton automatically handles OAuth flow and passes profile/token to the function
    def handle_auth_update(profile: gr.OAuthProfile | None = None, token: gr.OAuthToken | None = None):
        return update_ui_for_auth_status(profile, token)
    
    # Update UI when login button is clicked (handles both login and logout)
    login_button.click(
        handle_auth_update,
        inputs=[],
        outputs=[input, btn],
        queue=False
    )
    
    # Also update UI when the page loads in case user is already authenticated
    demo.load(
        handle_auth_update,
        inputs=[],
        outputs=[input, btn],
        queue=False
    )

if __name__ == "__main__":
    # Initialize Gradio documentation system
    initialize_gradio_docs()
    
    # Initialize ComfyUI documentation system
    initialize_comfyui_docs()
    
    # Initialize FastRTC documentation system
    initialize_fastrtc_docs()
    
    demo.queue(api_open=False, default_concurrency_limit=20).launch(
        show_api=False, 
        ssr_mode=True, 
        mcp_server=False
    )