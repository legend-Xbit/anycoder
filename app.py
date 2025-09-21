import os
import re
from http import HTTPStatus
from typing import Dict, List, Optional, Tuple
import base64
import mimetypes
import PyPDF2
import docx
import cv2
import numpy as np
from PIL import Image
import pytesseract
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
from tavily import TavilyClient
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
from dashscope.utils.oss_utils import check_and_upload_local

# Gradio supported languages for syntax highlighting
GRADIO_SUPPORTED_LANGUAGES = [
    "python", "c", "cpp", "markdown", "latex", "json", "html", "css", "javascript", "jinja2", "typescript", "yaml", "dockerfile", "shell", "r", "sql", "sql-msSQL", "sql-mySQL", "sql-mariaDB", "sql-sqlite", "sql-cassandra", "sql-plSQL", "sql-hive", "sql-pgSQL", "sql-gql", "sql-gpSQL", "sql-sparkSQL", "sql-esper", None
]

def get_gradio_language(language):
    # Map composite options to a supported syntax highlighting
    if language == "streamlit":
        return "python"
    if language == "gradio":
        return "python"
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
_gradio_docs_content: Optional[str] = None
_gradio_docs_last_fetched: Optional[datetime] = None

def fetch_gradio_docs() -> Optional[str]:
    """Fetch the latest Gradio documentation from llms.txt"""
    try:
        response = requests.get(GRADIO_LLMS_TXT_URL, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Warning: Failed to fetch Gradio docs from {GRADIO_LLMS_TXT_URL}: {e}")
        return None

def load_cached_gradio_docs() -> Optional[str]:
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
        _gradio_docs_content = latest_content
        _gradio_docs_last_fetched = datetime.now()
        save_gradio_docs_cache(latest_content)
        update_gradio_system_prompts()
        print("✅ Gradio documentation updated successfully")
        return True
    else:
        print("❌ Failed to update Gradio documentation")
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
            _gradio_docs_content = latest_content
            _gradio_docs_last_fetched = datetime.now()
            save_gradio_docs_cache(latest_content)
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

def update_gradio_system_prompts():
    """Update the global Gradio system prompts with latest documentation"""
    global GRADIO_SYSTEM_PROMPT, GRADIO_SYSTEM_PROMPT_WITH_SEARCH
    
    docs_content = get_gradio_docs_content()
    
    # Base system prompt
    base_prompt = """You are an expert Gradio developer. Write clean, idiomatic, and runnable Gradio applications for the user's request. Use the latest Gradio API and best practices. Output ONLY the code inside a ``` code block, and do not include any explanations or extra text. If the user provides a file or other context, use it as a reference. Make the app as self-contained as possible. Do NOT add the language name at the top of the code output.

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

## Complete Gradio API Reference

This reference is automatically synced from https://www.gradio.app/llms.txt to ensure accuracy.

"""
    
    # Search-enabled prompt
    search_prompt = """You are an expert Gradio developer with access to real-time web search. Write clean, idiomatic, and runnable Gradio applications for the user's request. Use the latest Gradio API and best practices. When needed, use web search to find current best practices or verify latest Gradio features. Output ONLY the code inside a ``` code block, and do not include any explanations or extra text. If the user provides a file or other context, use it as a reference. Make the app as self-contained as possible. Do NOT add the language name at the top of the code output.

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

For production Spaces with heavy models, use ahead-of-time (AoT) compilation for 1.3x-1.8x speedups:

### Basic AoT Compilation
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

## Complete Gradio API Reference

This reference is automatically synced from https://www.gradio.app/llms.txt to ensure accuracy.

"""
    
    # Update the prompts
    GRADIO_SYSTEM_PROMPT = base_prompt + docs_content + "\n\nAlways use the exact function signatures from this API reference and follow modern Gradio patterns.\n\nIMPORTANT: Always include \"Built with anycoder\" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder"
    GRADIO_SYSTEM_PROMPT_WITH_SEARCH = search_prompt + docs_content + "\n\nAlways use the exact function signatures from this API reference and follow modern Gradio patterns.\n\nIMPORTANT: Always include \"Built with anycoder\" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder"

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

# Configuration
HTML_SYSTEM_PROMPT = """ONLY USE HTML, CSS AND JAVASCRIPT. If you want to use ICON make sure to import the library first. Try to create the best UI possible by using only HTML, CSS and JAVASCRIPT. MAKE IT RESPONSIVE USING MODERN CSS. Use as much as you can modern CSS for the styling, if you can't do something with modern CSS, then use custom CSS. Also, try to elaborate as much as you can, to create something unique. ALWAYS GIVE THE RESPONSE INTO A SINGLE HTML FILE

For website redesign tasks:
- Use the provided original HTML code as the starting point for redesign
- Preserve all original content, structure, and functionality
- Keep the same semantic HTML structure but enhance the styling
- Reuse all original images and their URLs from the HTML code
- Create a modern, responsive design with improved typography and spacing
- Use modern CSS frameworks and design patterns
- Ensure accessibility and mobile responsiveness
- Maintain the same navigation and user flow
- Enhance the visual design while keeping the original layout structure

If an image is provided, analyze it and use the visual information to better understand the user's requirements.

Always respond with code that can be executed or rendered directly.

Always output only the HTML code inside a ```html ... ``` code block, and do not include any explanations or extra text. Do NOT add the language name at the top of the code output.

IMPORTANT: Always include "Built with anycoder" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder"""

def validate_video_html(video_html: str) -> bool:
    """Validate that the video HTML is well-formed and safe to insert."""
    try:
        # Basic checks for video HTML structure
        if not video_html or not video_html.strip():
            return False
        
        # Check for required video elements
        if '<video' not in video_html or '</video>' not in video_html:
            return False
        
        # Check for proper source tag
        if '<source' not in video_html:
            return False
        
        # Check for valid video source (data URI, HF URL, or file URL)
        has_data_uri = 'data:video/mp4;base64,' in video_html
        has_hf_url = 'https://huggingface.co/datasets/' in video_html and '/resolve/main/' in video_html
        has_file_url = 'file://' in video_html
        if not (has_data_uri or has_hf_url or has_file_url):
            return False
        
        # Basic HTML structure validation
        video_start = video_html.find('<video')
        video_end = video_html.find('</video>') + 8
        if video_start == -1 or video_end == 7:  # 7 means </video> not found
            return False
        
        return True
    except Exception:
        return False

def llm_place_media(html_content: str, media_html_tag: str, media_kind: str = "image") -> str:
    """Ask a lightweight model to produce search/replace blocks that insert media_html_tag in the best spot.

    The model must return ONLY our block format using SEARCH_START/DIVIDER/REPLACE_END.
    """
    try:
        client = get_inference_client("Qwen/Qwen3-Coder-480B-A35B-Instruct", "auto")
        system_prompt = (
            "You are a code editor. Insert the provided media tag into the given HTML in the most semantically appropriate place.\n"
            "For video elements: prefer replacing placeholder images or inserting in hero sections with proper container divs.\n"
            "For image elements: prefer replacing placeholder images or inserting near related content.\n"
            "CRITICAL: Ensure proper HTML structure - videos should be wrapped in appropriate containers.\n"
            "Return ONLY search/replace blocks using the exact markers: <<<<<<< SEARCH, =======, >>>>>>> REPLACE.\n"
            "Do NOT include any commentary. Ensure the SEARCH block matches exact lines from the input.\n"
            "When inserting videos, ensure they are properly contained within semantic HTML elements.\n"
        )
        # Truncate very long media tags for LLM prompt only to prevent token limits
        truncated_media_tag_for_prompt = media_html_tag
        if len(media_html_tag) > 2000:
            # For very long data URIs, show structure but truncate the data for LLM prompt
            if 'data:video/mp4;base64,' in media_html_tag:
                start_idx = media_html_tag.find('data:video/mp4;base64,')
                end_idx = media_html_tag.find('"', start_idx)
                if start_idx != -1 and end_idx != -1:
                    truncated_media_tag_for_prompt = (
                        media_html_tag[:start_idx] + 
                        'data:video/mp4;base64,[TRUNCATED_BASE64_DATA]' + 
                        media_html_tag[end_idx:]
                    )
        
        user_payload = (
            "HTML Document:\n" + html_content + "\n\n" +
            f"Media ({media_kind}):\n" + truncated_media_tag_for_prompt + "\n\n" +
            "Produce search/replace blocks now."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_payload},
        ]
        completion = client.chat.completions.create(
            model="Qwen/Qwen3-Coder-480B-A35B-Instruct",
            messages=messages,
            max_tokens=2000,
            temperature=0.2,
        )
        text = (completion.choices[0].message.content or "") if completion and completion.choices else ""
        
        # Replace any truncated placeholders with the original full media HTML
        if '[TRUNCATED_BASE64_DATA]' in text and 'data:video/mp4;base64,[TRUNCATED_BASE64_DATA]' in truncated_media_tag_for_prompt:
            # Extract the original base64 data from the full media tag
            original_start = media_html_tag.find('data:video/mp4;base64,')
            original_end = media_html_tag.find('"', original_start)
            if original_start != -1 and original_end != -1:
                original_data_uri = media_html_tag[original_start:original_end]
                text = text.replace('data:video/mp4;base64,[TRUNCATED_BASE64_DATA]', original_data_uri)
        
        return text.strip()
    except Exception as e:
        print(f"[LLMPlaceMedia] Fallback due to error: {e}")
        return ""

# Stricter prompt for GLM-4.5V to ensure a complete, runnable HTML document with no escaped characters
GLM45V_HTML_SYSTEM_PROMPT = """You are an expert front-end developer.

Output a COMPLETE, STANDALONE HTML document that renders directly in a browser.

Hard constraints:
- DO NOT use React, ReactDOM, JSX, Babel, Vue, Angular, Svelte, or any SPA framework.
- Use ONLY plain HTML, CSS, and vanilla JavaScript.
- Allowed external resources: Tailwind CSS CDN, Font Awesome CDN, Google Fonts.
- Do NOT escape characters (no \\n, \\t, or escaped quotes). Output raw HTML/JS/CSS.

Structural requirements:
- Include <!DOCTYPE html>, <html>, <head>, and <body> with proper nesting
- Include required <link> tags for any CSS you reference (e.g., Tailwind, Font Awesome, Google Fonts)
- Keep everything in ONE file; inline CSS/JS as needed

Return ONLY the code inside a single ```html ... ``` code block. No additional text before or after.

IMPORTANT: Always include "Built with anycoder" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder
"""

# ---------------------------------------------------------------------------
# Video temp-file management (per-session tracking and cleanup)
# ---------------------------------------------------------------------------
VIDEO_TEMP_DIR = os.path.join(tempfile.gettempdir(), "anycoder_videos")
VIDEO_FILE_TTL_SECONDS = 6 * 60 * 60  # 6 hours
_SESSION_VIDEO_FILES: Dict[str, List[str]] = {}
_VIDEO_FILES_LOCK = threading.Lock()


def _ensure_video_dir_exists() -> None:
    try:
        os.makedirs(VIDEO_TEMP_DIR, exist_ok=True)
    except Exception:
        pass


def _register_video_for_session(session_id: Optional[str], file_path: str) -> None:
    if not session_id or not file_path:
        return
    with _VIDEO_FILES_LOCK:
        if session_id not in _SESSION_VIDEO_FILES:
            _SESSION_VIDEO_FILES[session_id] = []
        _SESSION_VIDEO_FILES[session_id].append(file_path)


def cleanup_session_videos(session_id: Optional[str]) -> None:
    if not session_id:
        return
    with _VIDEO_FILES_LOCK:
        file_list = _SESSION_VIDEO_FILES.pop(session_id, [])
    for path in file_list:
        try:
            if path and os.path.exists(path):
                os.unlink(path)
        except Exception:
            # Best-effort cleanup
            pass


def reap_old_videos(ttl_seconds: int = VIDEO_FILE_TTL_SECONDS) -> None:
    """Delete old video files in the temp directory based on modification time."""
    try:
        _ensure_video_dir_exists()
        now_ts = time.time()
        for name in os.listdir(VIDEO_TEMP_DIR):
            path = os.path.join(VIDEO_TEMP_DIR, name)
            try:
                if not os.path.isfile(path):
                    continue
                mtime = os.path.getmtime(path)
                if now_ts - mtime > ttl_seconds:
                    os.unlink(path)
            except Exception:
                pass
    except Exception:
        # Temp dir might not exist or be accessible; ignore
        pass

# ---------------------------------------------------------------------------
# Audio temp-file management (per-session tracking and cleanup)
# ---------------------------------------------------------------------------
AUDIO_TEMP_DIR = os.path.join(tempfile.gettempdir(), "anycoder_audio")
AUDIO_FILE_TTL_SECONDS = 6 * 60 * 60  # 6 hours
_SESSION_AUDIO_FILES: Dict[str, List[str]] = {}
_AUDIO_FILES_LOCK = threading.Lock()


def _ensure_audio_dir_exists() -> None:
    try:
        os.makedirs(AUDIO_TEMP_DIR, exist_ok=True)
    except Exception:
        pass


def _register_audio_for_session(session_id: Optional[str], file_path: str) -> None:
    if not session_id or not file_path:
        return
    with _AUDIO_FILES_LOCK:
        if session_id not in _SESSION_AUDIO_FILES:
            _SESSION_AUDIO_FILES[session_id] = []
        _SESSION_AUDIO_FILES[session_id].append(file_path)


def cleanup_session_audio(session_id: Optional[str]) -> None:
    if not session_id:
        return
    with _AUDIO_FILES_LOCK:
        file_list = _SESSION_AUDIO_FILES.pop(session_id, [])
    for path in file_list:
        try:
            if path and os.path.exists(path):
                os.unlink(path)
        except Exception:
            pass


def reap_old_audio(ttl_seconds: int = AUDIO_FILE_TTL_SECONDS) -> None:
    try:
        _ensure_audio_dir_exists()
        now_ts = time.time()
        for name in os.listdir(AUDIO_TEMP_DIR):
            path = os.path.join(AUDIO_TEMP_DIR, name)
            try:
                if not os.path.isfile(path):
                    continue
                mtime = os.path.getmtime(path)
                if now_ts - mtime > ttl_seconds:
                    os.unlink(path)
            except Exception:
                pass
    except Exception:
        pass

TRANSFORMERS_JS_SYSTEM_PROMPT = """You are an expert web developer creating a transformers.js application. You will generate THREE separate files: index.html, index.js, and style.css.

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

Always output only the three code blocks as shown above, and do not include any explanations or extra text.

IMPORTANT: Always include "Built with anycoder" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder"""

SVELTE_SYSTEM_PROMPT = """You are an expert Svelte developer creating a modern Svelte application.

File selection policy (dynamic, model-decided):
- Generate ONLY the files actually needed for the user's request.
- MUST include src/App.svelte (entry component) and src/main.ts (entry point).
- Usually include src/app.css for global styles.
- Add additional files when needed, e.g. src/lib/*.svelte, src/components/*.svelte, src/stores/*.ts, static/* assets, etc.
- Other base template files (package.json, vite.config.ts, tsconfig, svelte.config.js, src/vite-env.d.ts) are provided by the template and should NOT be generated unless explicitly requested by the user.

CRITICAL: Always generate src/main.ts with correct Svelte 5 syntax:
```typescript
import './app.css'
import App from './App.svelte'

const app = new App({
  target: document.getElementById('app')!,
})

export default app
```
Do NOT use the old mount syntax: `import { mount } from 'svelte'` - this will cause build errors.

Output format (CRITICAL):
- Return ONLY a series of file sections, each starting with a filename line:
  === src/App.svelte ===
  ...file content...

  === src/app.css ===
  ...file content...

  (repeat for all files you decide to create)
- Do NOT wrap files in Markdown code fences.

Dependency policy:
- If you import any third-party npm packages (e.g., "@gradio/dataframe"), include a package.json at the project root with a "dependencies" section listing them. Keep scripts and devDependencies compatible with the default Svelte + Vite template.

Requirements:
1. Create a modern, responsive Svelte application based on the user's specific request
2. Prefer TypeScript where applicable for better type safety
3. Create a clean, professional UI with good user experience
4. Make the application fully responsive for mobile devices
5. Use modern CSS practices and Svelte best practices
6. Include proper error handling and loading states
7. Follow accessibility best practices
8. Use Svelte's reactive features effectively
9. Include proper component structure and organization (only what's needed)

IMPORTANT: Always include "Built with anycoder" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder
"""

SVELTE_SYSTEM_PROMPT_WITH_SEARCH = """You are an expert Svelte developer. You have access to real-time web search.

File selection policy (dynamic, model-decided):
- Generate ONLY the files actually needed for the user's request.
- MUST include src/App.svelte (entry component) and src/main.ts (entry point).
- Usually include src/app.css for global styles.
- Add additional files when needed, e.g. src/lib/*.svelte, src/components/*.svelte, src/stores/*.ts, static/* assets, etc.
- Other base template files (package.json, vite.config.ts, tsconfig, svelte.config.js, src/vite-env.d.ts) are provided by the template and should NOT be generated unless explicitly requested by the user.

CRITICAL: Always generate src/main.ts with correct Svelte 5 syntax:
```typescript
import './app.css'
import App from './App.svelte'

const app = new App({
  target: document.getElementById('app')!,
})

export default app
```
Do NOT use the old mount syntax: `import { mount } from 'svelte'` - this will cause build errors.

Output format (CRITICAL):
- Return ONLY a series of file sections, each starting with a filename line:
  === src/App.svelte ===
  ...file content...

  === src/app.css ===
  ...file content...

  (repeat for all files you decide to create)
- Do NOT wrap files in Markdown code fences.

Dependency policy:
- If you import any third-party npm packages, include a package.json at the project root with a "dependencies" section listing them. Keep scripts and devDependencies compatible with the default Svelte + Vite template.

Requirements:
1. Create a modern, responsive Svelte application
2. Prefer TypeScript where applicable
3. Clean, professional UI and UX
4. Mobile-first responsiveness
5. Svelte best practices and modern CSS
6. Error handling and loading states
7. Accessibility best practices
8. Use search to apply current best practices
9. Keep component structure organized and minimal

IMPORTANT: Always include "Built with anycoder" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder
"""

TRANSFORMERS_JS_SYSTEM_PROMPT_WITH_SEARCH = """You are an expert web developer creating a transformers.js application. You have access to real-time web search. When needed, use web search to find the latest information, best practices, or specific technologies for transformers.js.

You will generate THREE separate files: index.html, index.js, and style.css.

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
3. Use web search to find current best practices and latest transformers.js features
4. Create a clean, professional UI with good user experience
5. Make the application fully responsive for mobile devices
6. Use modern CSS practices and JavaScript ES6+ features
7. Include proper error handling and loading states
8. Follow accessibility best practices

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

Always output only the three code blocks as shown above, and do not include any explanations or extra text.

IMPORTANT: Always include "Built with anycoder" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder"""

# Gradio system prompts will be dynamically populated by update_gradio_system_prompts()
GRADIO_SYSTEM_PROMPT = ""
GRADIO_SYSTEM_PROMPT_WITH_SEARCH = ""

# GRADIO_SYSTEM_PROMPT_WITH_SEARCH will be dynamically populated by update_gradio_system_prompts()

# All Gradio API documentation is now dynamically loaded from https://www.gradio.app/llms.txt

GENERIC_SYSTEM_PROMPT = """You are an expert {language} developer. Write clean, idiomatic, and runnable {language} code for the user's request. If possible, include comments and best practices. Output ONLY the code inside a ``` code block, and do not include any explanations or extra text. If the user provides a file or other context, use it as a reference. If the code is for a script or app, make it as self-contained as possible. Do NOT add the language name at the top of the code output.

IMPORTANT: Always include "Built with anycoder" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder"""

# System prompt with search capability
HTML_SYSTEM_PROMPT_WITH_SEARCH = """You are an expert front-end developer. You have access to real-time web search.

Output a COMPLETE, STANDALONE HTML document that renders directly in a browser. Requirements:
- Include <!DOCTYPE html>, <html>, <head>, and <body> with proper nesting
- Include all required <link> and <script> tags for any libraries you use
- Do NOT escape characters (no \\n, \\t, or escaped quotes). Output raw HTML/JS/CSS.
- If you use React or Tailwind, include correct CDN tags
- Keep everything in ONE file; inline CSS/JS as needed

Use web search when needed to find the latest best practices or correct CDN links.

For website redesign tasks:
- Use the provided original HTML code as the starting point for redesign
- Preserve all original content, structure, and functionality
- Keep the same semantic HTML structure but enhance the styling
- Reuse all original images and their URLs from the HTML code
- Use web search to find current design trends and best practices for the specific type of website
- Create a modern, responsive design with improved typography and spacing
- Use modern CSS frameworks and design patterns
- Ensure accessibility and mobile responsiveness
- Maintain the same navigation and user flow
- Enhance the visual design while keeping the original layout structure

If an image is provided, analyze it and use the visual information to better understand the user's requirements.

Always respond with code that can be executed or rendered directly.

Always output only the HTML code inside a ```html ... ``` code block, and do not include any explanations or extra text. Do NOT add the language name at the top of the code output.

IMPORTANT: Always include "Built with anycoder" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder"""

# Multi-page static HTML project prompt (generic, production-style structure)
MULTIPAGE_HTML_SYSTEM_PROMPT = """You are an expert front-end developer.

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

# Multi-page with search augmentation
MULTIPAGE_HTML_SYSTEM_PROMPT_WITH_SEARCH = """You are an expert front-end developer. You have access to real-time web search.

Create a production-ready MULTI-PAGE website using ONLY HTML, CSS, and vanilla JavaScript. Do NOT use SPA frameworks.

Follow the same file output format and project structure as specified:
=== filename === blocks for each file (no Markdown fences)

Use search results to apply current best practices in accessibility, semantics, responsive meta tags, and performance (preconnect, responsive images).

IMPORTANT: Always include "Built with anycoder" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder
"""

# Dynamic multi-page (model decides files) prompts
DYNAMIC_MULTIPAGE_HTML_SYSTEM_PROMPT = """You are an expert front-end developer.

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

DYNAMIC_MULTIPAGE_HTML_SYSTEM_PROMPT_WITH_SEARCH = """You are an expert front-end developer. You have access to real-time web search.

Create a production-ready website using ONLY HTML, CSS, and vanilla JavaScript. Do NOT use SPA frameworks.

Follow the same output format and file selection policy as above (=== filename === blocks; model decides which files to create; ensure index.html unless explicitly not needed).

Use search results to apply current best practices in accessibility, semantics, responsive meta tags, and performance (preconnect, responsive images).

IMPORTANT: Always include "Built with anycoder" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder
"""

GENERIC_SYSTEM_PROMPT_WITH_SEARCH = """You are an expert {language} developer. You have access to real-time web search. When needed, use web search to find the latest information, best practices, or specific technologies for {language}.

Write clean, idiomatic, and runnable {language} code for the user's request. If possible, include comments and best practices. Output ONLY the code inside a ``` code block, and do not include any explanations or extra text. If the user provides a file or other context, use it as a reference. If the code is for a script or app, make it as self-contained as possible. Do NOT add the language name at the top of the code output.

IMPORTANT: Always include "Built with anycoder" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder"""

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
- app.py (main application file)
- requirements.txt (dependencies)
- Other supporting files as needed

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
        "name": "Grok 4 Fast (Free)",
        "id": "x-ai/grok-4-fast:free",
        "description": "X.AI Grok 4 Fast model via OpenRouter - free tier with vision capabilities for code generation"
    },
    {
        "name": "Moonshot Kimi-K2",
        "id": "moonshotai/Kimi-K2-Instruct",
        "description": "Moonshot AI Kimi-K2-Instruct model for code generation and general tasks"
    },
    {
        "name": "Kimi K2 Turbo (Preview)",
        "id": "kimi-k2-turbo-preview",
        "description": "Moonshot AI Kimi K2 Turbo via OpenAI-compatible API"
    },
    {
        "name": "Carrot",
        "id": "stealth-model-1",
        "description": "High-performance AI model for code generation and complex reasoning tasks"
    },
    {
        "name": "DeepSeek V3",
        "id": "deepseek-ai/DeepSeek-V3-0324",
        "description": "DeepSeek V3 model for code generation"
    },
    {
        "name": "DeepSeek V3.1",
        "id": "deepseek-ai/DeepSeek-V3.1",
        "description": "DeepSeek V3.1 model for code generation and general tasks"
    },
    {
        "name": "DeepSeek R1", 
        "id": "deepseek-ai/DeepSeek-R1-0528",
        "description": "DeepSeek R1 model for code generation"
    },
    {
        "name": "ERNIE-4.5-VL",
        "id": "baidu/ERNIE-4.5-VL-424B-A47B-Base-PT",
        "description": "ERNIE-4.5-VL model for multimodal code generation with image support"
    },
    {
        "name": "MiniMax M1",
        "id": "MiniMaxAI/MiniMax-M1-80k",
        "description": "MiniMax M1 model for code generation and general tasks"
    },
    {
        "name": "Qwen3-235B-A22B",
        "id": "Qwen/Qwen3-235B-A22B",
        "description": "Qwen3-235B-A22B model for code generation and general tasks"
    },
    {
        "name": "SmolLM3-3B",
        "id": "HuggingFaceTB/SmolLM3-3B",
        "description": "SmolLM3-3B model for code generation and general tasks"
    },
    {
        "name": "GLM-4.5",
        "id": "zai-org/GLM-4.5",
        "description": "GLM-4.5 model with thinking capabilities for advanced code generation"
    },
    {
        "name": "GLM-4.5V",
        "id": "zai-org/GLM-4.5V",
        "description": "GLM-4.5V multimodal model with image understanding for code generation"
    },
    {
        "name": "GLM-4.1V-9B-Thinking",
        "id": "THUDM/GLM-4.1V-9B-Thinking",
        "description": "GLM-4.1V-9B-Thinking model for multimodal code generation with image support"
    },
    {
        "name": "Qwen3-235B-A22B-Instruct-2507",
        "id": "Qwen/Qwen3-235B-A22B-Instruct-2507",
        "description": "Qwen3-235B-A22B-Instruct-2507 model for code generation and general tasks"
    },
    {
        "name": "Qwen3-Coder-480B-A35B-Instruct",
        "id": "Qwen/Qwen3-Coder-480B-A35B-Instruct",
        "description": "Qwen3-Coder-480B-A35B-Instruct model for advanced code generation and programming tasks"
    },
    {
        "name": "Qwen3-32B",
        "id": "Qwen/Qwen3-32B",
        "description": "Qwen3-32B model for code generation and general tasks"
    },
    {
        "name": "Qwen3-4B-Instruct-2507",
        "id": "Qwen/Qwen3-4B-Instruct-2507",
        "description": "Qwen3-4B-Instruct-2507 model for code generation and general tasks"
    },
    {
        "name": "Qwen3-4B-Thinking-2507",
        "id": "Qwen/Qwen3-4B-Thinking-2507",
        "description": "Qwen3-4B-Thinking-2507 model with advanced reasoning capabilities for code generation and general tasks"
    },
    {
        "name": "Qwen3-235B-A22B-Thinking",
        "id": "Qwen/Qwen3-235B-A22B-Thinking-2507",
        "description": "Qwen3-235B-A22B-Thinking model with advanced reasoning capabilities"
    },
    {
        "name": "Qwen3-Next-80B-A3B-Thinking",
        "id": "Qwen/Qwen3-Next-80B-A3B-Thinking",
        "description": "Qwen3-Next-80B-A3B-Thinking model with advanced reasoning capabilities via Hyperbolic"
    },
    {
        "name": "Qwen3-Next-80B-A3B-Instruct",
        "id": "Qwen/Qwen3-Next-80B-A3B-Instruct",
        "description": "Qwen3-Next-80B-A3B-Instruct model for code generation and general tasks via Hyperbolic"
    },
    {
        "name": "Qwen3-30B-A3B-Instruct-2507",
        "id": "qwen3-30b-a3b-instruct-2507",
        "description": "Qwen3-30B-A3B-Instruct model via Alibaba Cloud DashScope API"
    },
    {
        "name": "Qwen3-30B-A3B-Thinking-2507",
        "id": "qwen3-30b-a3b-thinking-2507",
        "description": "Qwen3-30B-A3B-Thinking model with advanced reasoning via Alibaba Cloud DashScope API"
    },
    {
        "name": "Qwen3-Coder-30B-A3B-Instruct",
        "id": "qwen3-coder-30b-a3b-instruct",
        "description": "Qwen3-Coder-30B-A3B-Instruct model for advanced code generation via Alibaba Cloud DashScope API"
    },
    {
        "name": "Cohere Command-A Reasoning 08-2025",
        "id": "CohereLabs/command-a-reasoning-08-2025",
        "description": "Cohere Labs Command-A Reasoning (Aug 2025) via Hugging Face InferenceClient"
    },
    {
        "name": "StepFun Step-3",
        "id": "step-3",
        "description": "StepFun Step-3 model - AI chat assistant by 阶跃星辰 with multilingual capabilities"
    },
    {
        "name": "Codestral 2508",
        "id": "codestral-2508",
        "description": "Mistral Codestral model - specialized for code generation and programming tasks",
        "type": "mistral"
    },
    {
        "name": "Mistral Medium 2508",
        "id": "mistral-medium-2508",
        "description": "Mistral Medium 2508 model via Mistral API for general tasks and coding",
        "type": "mistral"
    },
    {
        "name": "Magistral Medium 2509",
        "id": "magistral-medium-2509",
        "description": "Magistral Medium 2509 model via Mistral API for advanced code generation and reasoning",
        "type": "mistral"
    },
    {
        "name": "Gemini 2.5 Flash",
        "id": "gemini-2.5-flash",
        "description": "Google Gemini 2.5 Flash via OpenAI-compatible API"
    },
    {
        "name": "Gemini 2.5 Pro",
        "id": "gemini-2.5-pro",
        "description": "Google Gemini 2.5 Pro via OpenAI-compatible API"
    },
    {
        "name": "GPT-OSS-120B",
        "id": "openai/gpt-oss-120b",
        "description": "OpenAI GPT-OSS-120B model for advanced code generation and general tasks"
    },
    {
        "name": "GPT-OSS-20B",
        "id": "openai/gpt-oss-20b",
        "description": "OpenAI GPT-OSS-20B model for code generation and general tasks"
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
        "name": "Qwen3 Max Preview",
        "id": "qwen3-max-preview",
        "description": "Qwen3 Max Preview model via DashScope International API"
    },
    {
        "name": "Sonoma Dusk Alpha",
        "id": "openrouter/sonoma-dusk-alpha",
        "description": "OpenRouter Sonoma Dusk Alpha model with vision capabilities"
    },
    {
        "name": "Sonoma Sky Alpha",
        "id": "openrouter/sonoma-sky-alpha",
        "description": "OpenRouter Sonoma Sky Alpha model with vision capabilities"
    }
]

# Default model selection
DEFAULT_MODEL_NAME = "Grok 4 Fast (Free)"
DEFAULT_MODEL = None
for _m in AVAILABLE_MODELS:
    if _m.get("name") == DEFAULT_MODEL_NAME:
        DEFAULT_MODEL = _m
        break
if DEFAULT_MODEL is None and AVAILABLE_MODELS:
    DEFAULT_MODEL = AVAILABLE_MODELS[0]
DEMO_LIST = [
    {
        "title": "Todo App",
        "description": "Create a simple todo application with add, delete, and mark as complete functionality"
    },
    {
        "title": "Calculator",
        "description": "Build a basic calculator with addition, subtraction, multiplication, and division"
    },
    {
        "title": "Chat Interface",
        "description": "Build a chat interface with message history and user input"
    },
    {
        "title": "E-commerce Product Card",
        "description": "Create a product card component for an e-commerce website"
    },
    {
        "title": "Login Form",
        "description": "Build a responsive login form with validation"
    },
    {
        "title": "Dashboard Layout",
        "description": "Create a dashboard layout with sidebar navigation and main content area"
    },
    {
        "title": "Data Table",
        "description": "Build a data table with sorting and filtering capabilities"
    },
    {
        "title": "Image Gallery",
        "description": "Create an image gallery with lightbox functionality and responsive grid layout"
    },
    {
        "title": "UI from Image",
        "description": "Upload an image of a UI design and I'll generate the HTML/CSS code for it"
    },
    {
        "title": "Extract Text from Image",
        "description": "Upload an image containing text and I'll extract and process the text content"
    },
    {
        "title": "Website Redesign",
        "description": "Enter a website URL to extract its content and redesign it with a modern, responsive layout"
    },
    {
        "title": "Modify HTML",
        "description": "After generating HTML, ask me to modify it with specific changes using search/replace format"
    },
    {
        "title": "Search/Replace Example",
        "description": "Generate HTML first, then ask: 'Change the title to My New Title' or 'Add a blue background to the body'"
    },
    {
        "title": "Transformers.js App",
        "description": "Create a transformers.js application with AI/ML functionality using the transformers.js library"
    },
    {
        "title": "Svelte App",
        "description": "Create a modern Svelte application with TypeScript, Vite, and responsive design"
    }
]

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
    elif model_id == "x-ai/grok-4-fast:free":
        # Use OpenRouter client for Grok 4 Fast (Free) model
        return OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://huggingface.co/spaces/akhaliq/anycoder",
                "X-Title": "anycoder"
            }
        )
    elif model_id == "step-3":
        # Use StepFun API client for Step-3 model
        return OpenAI(
            api_key=os.getenv("STEP_API_KEY"),
            base_url="https://api.stepfun.com/v1"
        )
    elif model_id == "codestral-2508" or model_id == "mistral-medium-2508" or model_id == "magistral-medium-2509":
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
    elif model_id == "kimi-k2-turbo-preview":
        # Use Moonshot AI (OpenAI-compatible) client for Kimi K2 Turbo (Preview)
        return OpenAI(
            api_key=os.getenv("MOONSHOT_API_KEY"),
            base_url="https://api.moonshot.ai/v1",
        )
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
    elif model_id == "openai/gpt-oss-120b":
        provider = "groq"
    elif model_id == "openai/gpt-oss-20b":
        provider = "groq"
    elif model_id == "moonshotai/Kimi-K2-Instruct":
        provider = "groq"
    elif model_id == "Qwen/Qwen3-235B-A22B":
        provider = "cerebras"
    elif model_id == "Qwen/Qwen3-235B-A22B-Instruct-2507":
        provider = "cerebras"
    elif model_id == "Qwen/Qwen3-32B":
        provider = "cerebras"
    elif model_id == "Qwen/Qwen3-235B-A22B-Thinking-2507":
        provider = "cerebras"
    elif model_id == "Qwen/Qwen3-Coder-480B-A35B-Instruct":
        provider = "cerebras"
    elif model_id == "Qwen/Qwen3-Next-80B-A3B-Thinking":
        provider = "hyperbolic"
    elif model_id == "Qwen/Qwen3-Next-80B-A3B-Instruct":
        provider = "novita"
    elif model_id == "deepseek-ai/DeepSeek-V3.1":
        provider = "novita"
    elif model_id == "zai-org/GLM-4.5":
        provider = "fireworks-ai"
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

# Tavily Search Client
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')
tavily_client = None
if TAVILY_API_KEY:
    try:
        tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
    except Exception as e:
        print(f"Failed to initialize Tavily client: {e}")
        tavily_client = None

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

def messages_to_history(messages: Messages) -> Tuple[str, History]:
    assert messages[0]['role'] == 'system'
    history = []
    for q, r in zip(messages[1::2], messages[2::2]):
        # Extract text content from multimodal messages for history
        user_content = q['content']
        if isinstance(user_content, list):
            text_content = ""
            for item in user_content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_content += item.get("text", "")
            user_content = text_content if text_content else str(user_content)
        
        history.append([user_content, r['content']])
    return history

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

def parse_svelte_output(text):
    """Parse Svelte output to extract individual files.

    Supports dynamic multi-file using === filename === sections (preferred),
    and falls back to ```svelte / ```css code blocks for minimal projects.
    """
    if not text:
        return {}

    # Preferred: multi-file sections (works for any filenames)
    try:
        files = parse_multipage_html_output(text) or {}
    except Exception:
        files = {}

    if isinstance(files, dict) and files:
        return files

    # Fallback: code fences for minimal two-file output
    import re
    results = {}
    svelte_match = re.search(r"```svelte\s*\n([\s\S]+?)\n```", text, re.IGNORECASE)
    if svelte_match:
        results['src/App.svelte'] = svelte_match.group(1).strip()
    css_match = re.search(r"```css\s*\n([\s\S]+?)\n```", text, re.IGNORECASE)
    if css_match:
        results['src/app.css'] = css_match.group(1).strip()
    return results

def format_svelte_output(files):
    """Format Svelte files into === filename === sections (generic)."""
    return format_multipage_output(files)

def infer_svelte_dependencies(files: Dict[str, str]) -> Dict[str, str]:
    """Infer npm dependencies from Svelte/TS imports across generated files.

    Returns mapping of package name -> semver (string). Uses conservative defaults
    when versions aren't known. Adds special-cased versions when known.
    """
    import re as _re
    deps: Dict[str, str] = {}
    import_from = _re.compile(r"import\s+[^;]*?from\s+['\"]([^'\"]+)['\"]", _re.IGNORECASE)
    bare_import = _re.compile(r"import\s+['\"]([^'\"]+)['\"]", _re.IGNORECASE)

    def maybe_add(pkg: str):
        if not pkg or pkg.startswith('.') or pkg.startswith('/') or pkg.startswith('http'):
            return
        if pkg.startswith('svelte'):
            return
        if pkg not in deps:
            # Default to wildcard; adjust known packages below
            deps[pkg] = "*"

    for path, content in (files or {}).items():
        if not isinstance(content, str):
            continue
        for m in import_from.finditer(content):
            maybe_add(m.group(1))
        for m in bare_import.finditer(content):
            maybe_add(m.group(1))

    # Pin known versions when sensible
    if '@gradio/dataframe' in deps:
        deps['@gradio/dataframe'] = '^0.19.1'

    return deps

def build_svelte_package_json(existing_json_text: Optional[str], detected_dependencies: Dict[str, str]) -> str:
    """Create or merge a package.json for Svelte spaces.

    - If existing_json_text is provided, merge detected deps into its dependencies.
    - Otherwise, start from the template defaults provided by the user and add deps.
    - Always preserve template scripts and devDependencies.
    """
    import json as _json
    # Template from the user's Svelte space scaffold
    template = {
        "name": "svelte",
        "private": True,
        "version": "0.0.0",
        "type": "module",
        "scripts": {
            "dev": "vite",
            "build": "vite build",
            "preview": "vite preview",
            "check": "svelte-check --tsconfig ./tsconfig.app.json && tsc -p tsconfig.node.json"
        },
        "devDependencies": {
            "@sveltejs/vite-plugin-svelte": "^5.0.3",
            "@tsconfig/svelte": "^5.0.4",
            "svelte": "^5.28.1",
            "svelte-check": "^4.1.6",
            "typescript": "~5.8.3",
            "vite": "^6.3.5"
        }
    }

    result = template
    if existing_json_text:
        try:
            parsed = _json.loads(existing_json_text)
            # Merge with template as base, keeping template scripts/devDependencies if missing in parsed
            result = {
                **template,
                **{k: v for k, v in parsed.items() if k not in ("scripts", "devDependencies")},
            }
            # If parsed contains its own scripts/devDependencies, prefer parsed to respect user's file
            if isinstance(parsed.get("scripts"), dict):
                result["scripts"] = parsed["scripts"]
            if isinstance(parsed.get("devDependencies"), dict):
                result["devDependencies"] = parsed["devDependencies"]
        except Exception:
            # Fallback to template if parse fails
            result = template

    # Merge dependencies
    existing_deps = result.get("dependencies", {})
    if not isinstance(existing_deps, dict):
        existing_deps = {}
    merged = {**existing_deps, **(detected_dependencies or {})}
    if merged:
        result["dependencies"] = merged
    else:
        result.pop("dependencies", None)

    return _json.dumps(result, indent=2, ensure_ascii=False) + "\n"

def history_render(history: History):
    return gr.update(visible=True), history

def clear_history():
    return [], [], None, ""  # Empty lists for both tuple format and chatbot messages, None for file, empty string for website URL

def update_image_input_visibility(model):
    """Update image input visibility based on selected model"""
    is_ernie_vl = model.get("id") == "baidu/ERNIE-4.5-VL-424B-A47B-Base-PT"
    is_glm_vl = model.get("id") == "THUDM/GLM-4.1V-9B-Thinking"
    is_glm_45v = model.get("id") == "zai-org/GLM-4.5V"
    return gr.update(visible=is_ernie_vl or is_glm_vl or is_glm_45v)

def process_image_for_model(image):
    """Convert image to base64 for model input"""
    if image is None:
        return None
    
    # Convert numpy array to PIL Image if needed
    import io
    import base64
    import numpy as np
    from PIL import Image
    
    # Handle numpy array from Gradio
    if isinstance(image, np.ndarray):
        image = Image.fromarray(image)
    
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{img_str}"

def compress_video_for_data_uri(video_bytes: bytes, max_size_mb: int = 8) -> bytes:
    """Compress video bytes for data URI embedding with size limit"""
    import subprocess
    import tempfile
    import os
    
    max_size = max_size_mb * 1024 * 1024
    
    # If already small enough, return as-is
    if len(video_bytes) <= max_size:
        return video_bytes
    
    print(f"[VideoCompress] Video size {len(video_bytes)} bytes exceeds {max_size_mb}MB limit, attempting compression")
    
    try:
        # Create temp files
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_input:
            temp_input.write(video_bytes)
            temp_input_path = temp_input.name
        
        temp_output_path = temp_input_path.replace('.mp4', '_compressed.mp4')
        
        try:
            # Compress with ffmpeg - extremely aggressive settings for tiny preview size
            subprocess.run([
                'ffmpeg', '-i', temp_input_path, 
                '-vcodec', 'libx264', '-crf', '40', '-preset', 'ultrafast',
                '-vf', 'scale=320:-1', '-r', '10',  # Very low resolution and frame rate
                '-an',  # Remove audio to save space
                '-t', '10',  # Limit to first 10 seconds for preview
                '-y', temp_output_path
            ], check=True, capture_output=True, stderr=subprocess.DEVNULL)
            
            # Read compressed video
            with open(temp_output_path, 'rb') as f:
                compressed_bytes = f.read()
            
            print(f"[VideoCompress] Compressed from {len(video_bytes)} to {len(compressed_bytes)} bytes")
            return compressed_bytes
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("[VideoCompress] ffmpeg compression failed, using original video")
            return video_bytes
        finally:
            # Clean up temp files
            for path in [temp_input_path, temp_output_path]:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except Exception:
                    pass
                    
    except Exception as e:
        print(f"[VideoCompress] Compression failed: {e}, using original video")
        return video_bytes

def compress_audio_for_data_uri(audio_bytes: bytes, max_size_mb: int = 4) -> bytes:
    """Compress audio bytes for data URI embedding with size limit"""
    import subprocess
    import tempfile
    import os
    
    max_size = max_size_mb * 1024 * 1024
    
    # If already small enough, return as-is
    if len(audio_bytes) <= max_size:
        return audio_bytes
    
    print(f"[AudioCompress] Audio size {len(audio_bytes)} bytes exceeds {max_size_mb}MB limit, attempting compression")
    
    try:
        # Create temp files
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_input:
            temp_input.write(audio_bytes)
            temp_input_path = temp_input.name
        
        temp_output_path = temp_input_path.replace('.wav', '_compressed.mp3')
        
        try:
            # Compress with ffmpeg - convert to MP3 with lower bitrate
            subprocess.run([
                'ffmpeg', '-i', temp_input_path,
                '-codec:a', 'libmp3lame', '-b:a', '64k',  # Low bitrate MP3
                '-y', temp_output_path
            ], check=True, capture_output=True, stderr=subprocess.DEVNULL)
            
            # Read compressed audio
            with open(temp_output_path, 'rb') as f:
                compressed_bytes = f.read()
            
            print(f"[AudioCompress] Compressed from {len(audio_bytes)} to {len(compressed_bytes)} bytes")
            return compressed_bytes
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("[AudioCompress] ffmpeg compression failed, using original audio")
            return audio_bytes
        finally:
            # Clean up temp files
            for path in [temp_input_path, temp_output_path]:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except Exception:
                    pass
                    
    except Exception as e:
        print(f"[AudioCompress] Compression failed: {e}, using original audio")
        return audio_bytes

# ---------------------------------------------------------------------------
# General temp media file management (per-session tracking and cleanup)
# ---------------------------------------------------------------------------
MEDIA_TEMP_DIR = os.path.join(tempfile.gettempdir(), "anycoder_media")
MEDIA_FILE_TTL_SECONDS = 6 * 60 * 60  # 6 hours
_SESSION_MEDIA_FILES: Dict[str, List[str]] = {}
_MEDIA_FILES_LOCK = threading.Lock()

# Global dictionary to store temporary media files for the session
temp_media_files = {}

def _ensure_media_dir_exists() -> None:
    """Ensure the media temp directory exists."""
    try:
        os.makedirs(MEDIA_TEMP_DIR, exist_ok=True)
    except Exception:
        pass

def track_session_media_file(session_id: Optional[str], file_path: str) -> None:
    """Track a media file for session-based cleanup."""
    if not session_id or not file_path:
        return
    with _MEDIA_FILES_LOCK:
        if session_id not in _SESSION_MEDIA_FILES:
            _SESSION_MEDIA_FILES[session_id] = []
        _SESSION_MEDIA_FILES[session_id].append(file_path)

def cleanup_session_media(session_id: Optional[str]) -> None:
    """Clean up media files for a specific session."""
    if not session_id:
        return
    with _MEDIA_FILES_LOCK:
        files_to_clean = _SESSION_MEDIA_FILES.pop(session_id, [])
    
    for path in files_to_clean:
        try:
            if path and os.path.exists(path):
                os.unlink(path)
        except Exception:
            # Best-effort cleanup
            pass

def reap_old_media(ttl_seconds: int = MEDIA_FILE_TTL_SECONDS) -> None:
    """Delete old media files in the temp directory based on modification time."""
    try:
        _ensure_media_dir_exists()
        now_ts = time.time()
        for name in os.listdir(MEDIA_TEMP_DIR):
            path = os.path.join(MEDIA_TEMP_DIR, name)
            if os.path.isfile(path):
                try:
                    mtime = os.path.getmtime(path)
                    if (now_ts - mtime) > ttl_seconds:
                        os.unlink(path)
                except Exception:
                    pass
    except Exception:
        # Temp dir might not exist or be accessible; ignore
        pass

def cleanup_all_temp_media_on_startup() -> None:
    """Clean up all temporary media files on app startup."""
    try:
        # Clean up temp_media_files registry
        temp_media_files.clear()
        
        # Clean up actual files from disk (assume all are orphaned on startup)
        _ensure_media_dir_exists()
        for name in os.listdir(MEDIA_TEMP_DIR):
            path = os.path.join(MEDIA_TEMP_DIR, name)
            if os.path.isfile(path):
                try:
                    os.unlink(path)
                except Exception:
                    pass
        
        # Clear session tracking
        with _MEDIA_FILES_LOCK:
            _SESSION_MEDIA_FILES.clear()
            
        print("[StartupCleanup] Cleaned up orphaned temporary media files")
    except Exception as e:
        print(f"[StartupCleanup] Error during media cleanup: {str(e)}")

def cleanup_all_temp_media_on_shutdown() -> None:
    """Clean up all temporary media files on app shutdown."""
    try:
        print("[ShutdownCleanup] Cleaning up temporary media files...")
        
        # Clean up temp_media_files registry and remove files
        for file_id, file_info in temp_media_files.items():
            try:
                if os.path.exists(file_info['path']):
                    os.unlink(file_info['path'])
            except Exception:
                pass
        temp_media_files.clear()
        
        # Clean up all session files
        with _MEDIA_FILES_LOCK:
            for session_id, file_paths in _SESSION_MEDIA_FILES.items():
                for path in file_paths:
                    try:
                        if path and os.path.exists(path):
                            os.unlink(path)
                    except Exception:
                        pass
            _SESSION_MEDIA_FILES.clear()
        
        print("[ShutdownCleanup] Temporary media cleanup completed")
    except Exception as e:
        print(f"[ShutdownCleanup] Error during cleanup: {str(e)}")

# Register shutdown cleanup handler
atexit.register(cleanup_all_temp_media_on_shutdown)

def create_temp_media_url(media_bytes: bytes, filename: str, media_type: str = "image", session_id: Optional[str] = None) -> str:
    """Create a temporary file and return a local URL for preview.
    
    Args:
        media_bytes: Raw bytes of the media file
        filename: Name for the file (will be made unique)
        media_type: Type of media ('image', 'video', 'audio')
        session_id: Session ID for tracking cleanup
    
    Returns:
        Temporary file URL for preview or error message
    """
    try:
        # Create unique filename with timestamp and UUID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        base_name, ext = os.path.splitext(filename)
        unique_filename = f"{media_type}_{timestamp}_{unique_id}_{base_name}{ext}"
        
        # Create temporary file in the dedicated directory
        _ensure_media_dir_exists()
        temp_path = os.path.join(MEDIA_TEMP_DIR, unique_filename)
        
        # Write media bytes to temporary file
        with open(temp_path, 'wb') as f:
            f.write(media_bytes)
        
        # Track file for session-based cleanup
        if session_id:
            track_session_media_file(session_id, temp_path)
        
        # Store the file info for later upload
        file_id = f"{media_type}_{unique_id}"
        temp_media_files[file_id] = {
            'path': temp_path,
            'filename': filename,
            'media_type': media_type,
            'media_bytes': media_bytes
        }
        
        # Return file:// URL for preview
        file_url = f"file://{temp_path}"
        print(f"[TempMedia] Created temporary {media_type} file: {file_url}")
        return file_url
        
    except Exception as e:
        print(f"[TempMedia] Failed to create temporary file: {str(e)}")
        return f"Error creating temporary {media_type} file: {str(e)}"

def upload_media_to_hf(media_bytes: bytes, filename: str, media_type: str = "image", token: gr.OAuthToken | None = None, use_temp: bool = True) -> str:
    """Upload media file to user's Hugging Face account or create temporary file.
    
    Args:
        media_bytes: Raw bytes of the media file
        filename: Name for the file (will be made unique)
        media_type: Type of media ('image', 'video', 'audio')
        token: OAuth token from gr.login (takes priority over env var)
        use_temp: If True, create temporary file for preview; if False, upload to HF
    
    Returns:
        Permanent URL to the uploaded file, temporary URL, or error message
    """
    try:
        # If use_temp is True, create temporary file for preview
        if use_temp:
            return create_temp_media_url(media_bytes, filename, media_type)
        
        # Otherwise, upload to Hugging Face for permanent URL
        # Try to get token from OAuth first, then fall back to environment variable
        hf_token = None
        if token and token.token:
            hf_token = token.token
        else:
            hf_token = os.getenv('HF_TOKEN')
        
        if not hf_token:
            return "Error: Please log in with your Hugging Face account to upload media, or set HF_TOKEN environment variable."
        
        # Initialize HF API
        api = HfApi(token=hf_token)
        
        # Get current user info to determine username
        try:
            user_info = api.whoami()
            username = user_info.get('name', 'unknown-user')
        except Exception as e:
            print(f"[HFUpload] Could not get user info: {e}")
            username = 'anycoder-user'
        
        # Create repository name for media storage
        repo_name = f"{username}/anycoder-media"
        
        # Try to create the repository if it doesn't exist
        try:
            api.create_repo(
                repo_id=repo_name,
                repo_type="dataset",
                private=False,
                exist_ok=True
            )
            print(f"[HFUpload] Repository {repo_name} ready")
        except Exception as e:
            print(f"[HFUpload] Repository creation/access issue: {e}")
            # Continue anyway, repo might already exist
        
        # Create unique filename with timestamp and UUID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        base_name, ext = os.path.splitext(filename)
        unique_filename = f"{media_type}/{timestamp}_{unique_id}_{base_name}{ext}"
        
        # Create temporary file for upload
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            temp_file.write(media_bytes)
            temp_path = temp_file.name
        
        try:
            # Upload file to HF repository
            api.upload_file(
                path_or_fileobj=temp_path,
                path_in_repo=unique_filename,
                repo_id=repo_name,
                repo_type="dataset",
                commit_message=f"Upload {media_type} generated by AnyCoder"
            )
            
            # Generate permanent URL
            permanent_url = f"https://huggingface.co/datasets/{repo_name}/resolve/main/{unique_filename}"
            print(f"[HFUpload] Successfully uploaded {media_type} to {permanent_url}")
            return permanent_url
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except Exception:
                pass
                
    except Exception as e:
        print(f"[HFUpload] Upload failed: {str(e)}")
        return f"Error uploading {media_type} to Hugging Face: {str(e)}"

def upload_temp_files_to_hf_and_replace_urls(html_content: str, token: gr.OAuthToken | None = None) -> str:
    """Upload all temporary media files to HF and replace their URLs in HTML content.
    
    Args:
        html_content: HTML content containing temporary file URLs
        token: OAuth token for HF authentication
    
    Returns:
        Updated HTML content with permanent HF URLs
    """
    try:
        if not temp_media_files:
            print("[DeployUpload] No temporary media files to upload")
            return html_content
        
        print(f"[DeployUpload] Uploading {len(temp_media_files)} temporary media files to HF")
        updated_content = html_content
        
        for file_id, file_info in temp_media_files.items():
            try:
                # Upload to HF with permanent URL
                permanent_url = upload_media_to_hf(
                    file_info['media_bytes'],
                    file_info['filename'], 
                    file_info['media_type'],
                    token,
                    use_temp=False  # Force permanent upload
                )
                
                if not permanent_url.startswith("Error"):
                    # Replace the temporary file URL with permanent URL
                    temp_url = f"file://{file_info['path']}"
                    updated_content = updated_content.replace(temp_url, permanent_url)
                    print(f"[DeployUpload] Replaced {temp_url} with {permanent_url}")
                else:
                    print(f"[DeployUpload] Failed to upload {file_id}: {permanent_url}")
            
            except Exception as e:
                print(f"[DeployUpload] Error uploading {file_id}: {str(e)}")
                continue
        
        # Clean up temporary files after upload
        cleanup_temp_media_files()
        
        return updated_content
        
    except Exception as e:
        print(f"[DeployUpload] Failed to upload temporary files: {str(e)}")
        return html_content

def cleanup_temp_media_files():
    """Clean up temporary media files from disk and memory."""
    try:
        for file_id, file_info in temp_media_files.items():
            try:
                if os.path.exists(file_info['path']):
                    os.remove(file_info['path'])
                    print(f"[TempCleanup] Removed {file_info['path']}")
            except Exception as e:
                print(f"[TempCleanup] Failed to remove {file_info['path']}: {str(e)}")
        
        # Clear the global dictionary
        temp_media_files.clear()
        print("[TempCleanup] Cleared temporary media files registry")
        
    except Exception as e:
        print(f"[TempCleanup] Error during cleanup: {str(e)}")

def generate_image_with_hunyuan(prompt: str, image_index: int = 0, token: gr.OAuthToken | None = None) -> str:
    """Generate image using Tencent HunyuanImage-2.1 via Hugging Face InferenceClient.
    
    Uses tencent/HunyuanImage-2.1 via HuggingFace InferenceClient with fal-ai provider.
    
    Returns an HTML <img> tag whose src is an uploaded temporary URL.
    """
    try:
        print(f"[Text2Image] Starting HunyuanImage generation with prompt: {prompt[:100]}...")
        
        # Check for HF_TOKEN
        hf_token = os.getenv('HF_TOKEN')
        if not hf_token:
            print("[Text2Image] Missing HF_TOKEN")
            return "Error: HF_TOKEN environment variable is not set. Please set it to your Hugging Face API token."

        from huggingface_hub import InferenceClient
        from PIL import Image
        import io as _io
        
        # Create InferenceClient with fal-ai provider
        client = InferenceClient(
            provider="fal-ai",
            api_key=hf_token,
            bill_to="huggingface",
        )
        
        print("[Text2Image] Making API request to HuggingFace InferenceClient...")
        
        # Generate image using HunyuanImage-2.1 model
        image = client.text_to_image(
            prompt,
            model="tencent/HunyuanImage-2.1",
        )
        
        print(f"[Text2Image] Successfully generated image with size: {image.size}")
        
        # Resize image to reduce size while maintaining quality
        max_size = 1024
        if image.width > max_size or image.height > max_size:
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Convert PIL Image to bytes for upload
        buffer = _io.BytesIO()
        # Save as JPEG with good quality
        image.convert('RGB').save(buffer, format='JPEG', quality=90, optimize=True)
        image_bytes = buffer.getvalue()
        
        # Upload and return HTML tag
        print("[Text2Image] Uploading image to HF...")
        filename = f"generated_image_{image_index}.jpg"
        temp_url = upload_media_to_hf(image_bytes, filename, "image", token, use_temp=True)
        if temp_url.startswith("Error"):
            print(f"[Text2Image] Upload failed: {temp_url}")
            return temp_url
        print(f"[Text2Image] Successfully generated image: {temp_url}")
        return f"<img src=\"{temp_url}\" alt=\"{prompt}\" style=\"max-width: 100%; height: auto; border-radius: 8px; margin: 10px 0;\" loading=\"lazy\" />"
        
    except Exception as e:
        print(f"[Text2Image] Error generating image with HunyuanImage: {str(e)}")
        return f"Error generating image (text-to-image): {str(e)}"

def generate_image_with_qwen(prompt: str, image_index: int = 0, token: gr.OAuthToken | None = None) -> str:
    """Generate image using Qwen image model via Hugging Face InferenceClient and upload to HF for permanent URL"""
    try:
        # Check if HF_TOKEN is available
        if not os.getenv('HF_TOKEN'):
            return "Error: HF_TOKEN environment variable is not set. Please set it to your Hugging Face API token."
        
        # Create InferenceClient for Qwen image generation
        client = InferenceClient(
            provider="auto",
            api_key=os.getenv('HF_TOKEN'),
            bill_to="huggingface",
        )
        
        # Generate image using Qwen/Qwen-Image model
        image = client.text_to_image(
            prompt,
            model="Qwen/Qwen-Image",
        )
        
        # Resize image to reduce size while maintaining quality
        max_size = 1024  # Increased size since we're not using data URIs
        if image.width > max_size or image.height > max_size:
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Convert PIL Image to bytes for upload
        import io
        buffer = io.BytesIO()
        # Save as JPEG with good quality since we're not embedding
        image.convert('RGB').save(buffer, format='JPEG', quality=90, optimize=True)
        image_bytes = buffer.getvalue()
        
        # Create temporary URL for preview (will be uploaded to HF during deploy)
        filename = f"generated_image_{image_index}.jpg"
        temp_url = upload_media_to_hf(image_bytes, filename, "image", token, use_temp=True)
        
        # Check if creation was successful
        if temp_url.startswith("Error"):
            return temp_url
        
        # Return HTML img tag with temporary URL
        return f'<img src="{temp_url}" alt="{prompt}" style="max-width: 100%; height: auto; border-radius: 8px; margin: 10px 0;" loading="lazy" />'
        
    except Exception as e:
        print(f"Image generation error: {str(e)}")
        return f"Error generating image: {str(e)}"

def generate_image_to_image(input_image_data, prompt: str, token: gr.OAuthToken | None = None) -> str:
    """Generate an image using image-to-image via OpenRouter.

    Uses Google Gemini 2.5 Flash Image Preview via OpenRouter chat completions API.

    Returns an HTML <img> tag whose src is an uploaded temporary URL.
    """
    try:
        # Check for OpenRouter API key
        openrouter_key = os.getenv('OPENROUTER_API_KEY')
        if not openrouter_key:
            return "Error: OPENROUTER_API_KEY environment variable is not set. Please set it to your OpenRouter API key."

        # Normalize input image to bytes
        import io
        from PIL import Image
        import base64
        import requests
        import json as _json
        try:
            import numpy as np
        except Exception:
            np = None

        if hasattr(input_image_data, 'read'):
            raw = input_image_data.read()
            pil_image = Image.open(io.BytesIO(raw))
        elif hasattr(input_image_data, 'mode') and hasattr(input_image_data, 'size'):
            pil_image = input_image_data
        elif np is not None and isinstance(input_image_data, np.ndarray):
            pil_image = Image.fromarray(input_image_data)
        elif isinstance(input_image_data, (bytes, bytearray)):
            pil_image = Image.open(io.BytesIO(input_image_data))
        else:
            pil_image = Image.open(io.BytesIO(bytes(input_image_data)))

        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')

        # Resize input image to avoid request body size limits
        max_input_size = 1024
        if pil_image.width > max_input_size or pil_image.height > max_input_size:
            pil_image.thumbnail((max_input_size, max_input_size), Image.Resampling.LANCZOS)

        # Convert to base64
        import io as _io
        buffered = _io.BytesIO()
        pil_image.save(buffered, format='PNG')
        img_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

        # Call OpenRouter API
        headers = {
            "Authorization": f"Bearer {openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("YOUR_SITE_URL", "https://example.com"),
            "X-Title": os.getenv("YOUR_SITE_NAME", "AnyCoder Image I2I"),
        }
        payload = {
            "model": "google/gemini-2.5-flash-image-preview:free",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                    ],
                }
            ],
            "max_tokens": 2048,
        }
        
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                data=_json.dumps(payload),
                timeout=60,
            )
            resp.raise_for_status()
            result_data = resp.json()
            
            # Corrected response parsing logic
            message = result_data.get('choices', [{}])[0].get('message', {})
            
            if message and 'images' in message and message['images']:
                # Get the first image from the 'images' list
                image_data = message['images'][0]
                base64_string = image_data.get('image_url', {}).get('url', '')
                
                if base64_string and ',' in base64_string:
                    # Remove the "data:image/png;base64," prefix
                    base64_content = base64_string.split(',')[1]
                    
                    # Decode the base64 string and create a PIL image
                    img_bytes = base64.b64decode(base64_content)
                    edited_image = Image.open(_io.BytesIO(img_bytes))
                    
                    # Convert PIL image to JPEG bytes for upload
                    out_buf = _io.BytesIO()
                    edited_image.convert('RGB').save(out_buf, format='JPEG', quality=90, optimize=True)
                    image_bytes = out_buf.getvalue()
                else:
                    raise RuntimeError(f"API returned an invalid image format. Response: {_json.dumps(result_data, indent=2)}")
            else:
                raise RuntimeError(f"API did not return an image. Full Response: {_json.dumps(result_data, indent=2)}")
                
        except requests.exceptions.HTTPError as err:
            error_body = err.response.text
            if err.response.status_code == 401:
                return "Error: Authentication failed. Check your OpenRouter API key."
            elif err.response.status_code == 429:
                return "Error: Rate limit exceeded or insufficient credits. Check your OpenRouter account."
            else:
                return f"Error: An API error occurred: {error_body}"
        except Exception as e:
            return f"Error: An unexpected error occurred: {str(e)}"

        # Upload and return HTML tag
        filename = "image_to_image_result.jpg"
        temp_url = upload_media_to_hf(image_bytes, filename, "image", token, use_temp=True)
        if temp_url.startswith("Error"):
            return temp_url
        return f"<img src=\"{temp_url}\" alt=\"{prompt}\" style=\"max-width: 100%; height: auto; border-radius: 8px; margin: 10px 0;\" loading=\"lazy\" />"
    except Exception as e:
        print(f"Image-to-image generation error: {str(e)}")
        return f"Error generating image (image-to-image): {str(e)}"

def generate_video_from_image(input_image_data, prompt: str, session_id: Optional[str] = None, token: gr.OAuthToken | None = None) -> str:
    """Generate a video from an input image and prompt using Hugging Face InferenceClient.

    Returns an HTML <video> tag whose source points to a local file URL (file://...).
    """
    try:
        print("[Image2Video] Starting video generation")
        if not os.getenv('HF_TOKEN'):
            print("[Image2Video] Missing HF_TOKEN")
            return "Error: HF_TOKEN environment variable is not set. Please set it to your Hugging Face API token."

        # Prepare client
        client = InferenceClient(
            provider="auto",
            api_key=os.getenv('HF_TOKEN'),
            bill_to="huggingface",
        )
        print(f"[Image2Video] InferenceClient initialized (provider=auto)")

        # Normalize input image to bytes, with downscale/compress to cap request size
        import io
        from PIL import Image
        try:
            import numpy as np
        except Exception:
            np = None

        def _load_pil(img_like) -> Image.Image:
            if hasattr(img_like, 'read'):
                return Image.open(io.BytesIO(img_like.read()))
            if hasattr(img_like, 'mode') and hasattr(img_like, 'size'):
                return img_like
            if np is not None and isinstance(img_like, np.ndarray):
                return Image.fromarray(img_like)
            if isinstance(img_like, (bytes, bytearray)):
                return Image.open(io.BytesIO(img_like))
            return Image.open(io.BytesIO(bytes(img_like)))

        pil_image = _load_pil(input_image_data)
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        try:
            print(f"[Image2Video] Input PIL image size={pil_image.size} mode={pil_image.mode}")
        except Exception:
            pass

        # Progressive encode to keep payload under ~3.9MB (below 4MB limit)
        MAX_BYTES = 3_900_000
        max_dim = 1024  # initial cap on longest edge
        quality = 90

        def encode_current(pil: Image.Image, q: int) -> bytes:
            tmp = io.BytesIO()
            pil.save(tmp, format='JPEG', quality=q, optimize=True)
            return tmp.getvalue()

        # Downscale while the longest edge exceeds max_dim
        while max(pil_image.size) > max_dim:
            ratio = max_dim / float(max(pil_image.size))
            new_size = (max(1, int(pil_image.size[0] * ratio)), max(1, int(pil_image.size[1] * ratio)))
            pil_image = pil_image.resize(new_size, Image.Resampling.LANCZOS)

        encoded = encode_current(pil_image, quality)
        # If still too big, iteratively reduce quality, then dimensions
        while len(encoded) > MAX_BYTES and (quality > 40 or max(pil_image.size) > 640):
            if quality > 40:
                quality -= 10
            else:
                # reduce dims by 15% if already at low quality
                new_w = max(1, int(pil_image.size[0] * 0.85))
                new_h = max(1, int(pil_image.size[1] * 0.85))
                pil_image = pil_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
            encoded = encode_current(pil_image, quality)

        input_bytes = encoded

        # Call image-to-video; require method support
        model_id = "Lightricks/LTX-Video-0.9.8-13B-distilled"
        image_to_video_method = getattr(client, "image_to_video", None)
        if not callable(image_to_video_method):
            print("[Image2Video] InferenceClient.image_to_video not available in this huggingface_hub version")
            return (
                "Error generating video (image-to-video): Your installed huggingface_hub version "
                "does not expose InferenceClient.image_to_video. Please upgrade with "
                "`pip install -U huggingface_hub` and try again."
            )
        print(f"[Image2Video] Calling image_to_video with model={model_id}, prompt length={len(prompt or '')}")
        video_bytes = image_to_video_method(
            input_bytes,
            prompt=prompt,
            model=model_id,
        )
        print(f"[Image2Video] Received video bytes: {len(video_bytes) if hasattr(video_bytes, '__len__') else 'unknown length'}")

        # Create temporary URL for preview (will be uploaded to HF during deploy)
        filename = "image_to_video_result.mp4"
        temp_url = upload_media_to_hf(video_bytes, filename, "video", token, use_temp=True)
        
        # Check if creation was successful
        if temp_url.startswith("Error"):
            return temp_url
        
        video_html = (
            f'<video controls autoplay muted loop playsinline '
            f'style="max-width: 100%; height: auto; border-radius: 8px; margin: 10px 0; display: block;" '
            f'onloadstart="this.style.backgroundColor=\'#f0f0f0\'" '
            f'onerror="this.style.display=\'none\'; console.error(\'Video failed to load\')">'
            f'<source src="{temp_url}" type="video/mp4" />'
            f'<p style="text-align: center; color: #666;">Your browser does not support the video tag.</p>'
            f'</video>'
        )
        
        print(f"[Image2Video] Successfully generated video HTML tag with temporary URL: {temp_url}")
        
        # Validate the generated video HTML
        if not validate_video_html(video_html):
            print("[Image2Video] Generated video HTML failed validation")
            return "Error: Generated video HTML is malformed"
        
        return video_html
    except Exception as e:
        import traceback
        print("[Image2Video] Exception during generation:")
        traceback.print_exc()
        print(f"Image-to-video generation error: {str(e)}")
        return f"Error generating video (image-to-video): {str(e)}"

def generate_video_from_text(prompt: str, session_id: Optional[str] = None, token: gr.OAuthToken | None = None) -> str:
    """Generate a video from a text prompt using Hugging Face InferenceClient.

    Returns an HTML <video> tag with compressed data URI for deployment compatibility.
    """
    try:
        print("[Text2Video] Starting video generation from text")
        if not os.getenv('HF_TOKEN'):
            print("[Text2Video] Missing HF_TOKEN")
            return "Error: HF_TOKEN environment variable is not set. Please set it to your Hugging Face API token."

        client = InferenceClient(
            provider="auto",
            api_key=os.getenv('HF_TOKEN'),
            bill_to="huggingface",
        )
        print("[Text2Video] InferenceClient initialized (provider=auto)")

        # Ensure the client has text_to_video (newer huggingface_hub)
        text_to_video_method = getattr(client, "text_to_video", None)
        if not callable(text_to_video_method):
            print("[Text2Video] InferenceClient.text_to_video not available in this huggingface_hub version")
            return (
                "Error generating video (text-to-video): Your installed huggingface_hub version "
                "does not expose InferenceClient.text_to_video. Please upgrade with "
                "`pip install -U huggingface_hub` and try again."
            )

        model_id = "Wan-AI/Wan2.2-T2V-A14B"
        prompt_str = (prompt or "").strip()
        print(f"[Text2Video] Calling text_to_video with model={model_id}, prompt length={len(prompt_str)}")
        video_bytes = text_to_video_method(
            prompt_str,
            model=model_id,
        )
        print(f"[Text2Video] Received video bytes: {len(video_bytes) if hasattr(video_bytes, '__len__') else 'unknown length'}")

        # Create temporary URL for preview (will be uploaded to HF during deploy)
        filename = "text_to_video_result.mp4"
        temp_url = upload_media_to_hf(video_bytes, filename, "video", token, use_temp=True)
        
        # Check if creation was successful
        if temp_url.startswith("Error"):
            return temp_url
        
        video_html = (
            f'<video controls autoplay muted loop playsinline '
            f'style="max-width: 100%; height: auto; border-radius: 8px; margin: 10px 0; display: block;" '
            f'onloadstart="this.style.backgroundColor=\'#f0f0f0\'" '
            f'onerror="this.style.display=\'none\'; console.error(\'Video failed to load\')">'
            f'<source src="{temp_url}" type="video/mp4" />'
            f'<p style="text-align: center; color: #666;">Your browser does not support the video tag.</p>'
            f'</video>'
        )
        
        print(f"[Text2Video] Successfully generated video HTML tag with temporary URL: {temp_url}")
        
        # Validate the generated video HTML
        if not validate_video_html(video_html):
            print("[Text2Video] Generated video HTML failed validation")
            return "Error: Generated video HTML is malformed"
        
        return video_html
    except Exception as e:
        import traceback
        print("[Text2Video] Exception during generation:")
        traceback.print_exc()
        print(f"Text-to-video generation error: {str(e)}")
        return f"Error generating video (text-to-video): {str(e)}"

def generate_video_from_video(input_video_data, prompt: str, session_id: Optional[str] = None, token: gr.OAuthToken | None = None) -> str:
    """Generate a video from an input video and prompt using Decart AI's Lucy Pro V2V API.
    
    Returns an HTML <video> tag whose source points to a temporary file URL.
    """
    try:
        print("[Video2Video] Starting video generation from video")
        
        # Check for Decart API key
        api_key = os.getenv('DECART_API_KEY')
        if not api_key:
            print("[Video2Video] Missing DECART_API_KEY")
            return "Error: DECART_API_KEY environment variable is not set. Please set it to your Decart AI API token."
        
        # Normalize input video to bytes
        import io
        import tempfile
        
        def _load_video_bytes(video_like) -> bytes:
            if hasattr(video_like, 'read'):
                return video_like.read()
            if isinstance(video_like, (bytes, bytearray)):
                return bytes(video_like)
            if hasattr(video_like, 'name'):  # File path
                with open(video_like.name, 'rb') as f:
                    return f.read()
            # If it's a string, assume it's a file path
            if isinstance(video_like, str):
                with open(video_like, 'rb') as f:
                    return f.read()
            return bytes(video_like)
        
        video_bytes = _load_video_bytes(input_video_data)
        print(f"[Video2Video] Input video size: {len(video_bytes)} bytes")
        
        # Prepare the API request
        form_data = {
            "prompt": prompt or "Enhance the video quality"
        }
        
        # Create temporary file for video data
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            temp_file.write(video_bytes)
            temp_file_path = temp_file.name
        
        try:
            # Make API request to Decart AI
            with open(temp_file_path, "rb") as video_file:
                files = {"data": video_file}
                headers = {"X-API-KEY": api_key}
                
                print(f"[Video2Video] Calling Decart API with prompt: {prompt}")
                response = requests.post(
                    "https://api.decart.ai/v1/generate/lucy-pro-v2v",
                    headers=headers,
                    data=form_data,
                    files=files,
                    timeout=300  # 5 minute timeout
                )
                
                if response.status_code != 200:
                    print(f"[Video2Video] API request failed with status {response.status_code}: {response.text}")
                    return f"Error: Decart API request failed with status {response.status_code}"
                
                result_video_bytes = response.content
                print(f"[Video2Video] Received video bytes: {len(result_video_bytes)}")
                
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass
        
        # Create temporary URL for preview (will be uploaded to HF during deploy)
        filename = "video_to_video_result.mp4"
        temp_url = upload_media_to_hf(result_video_bytes, filename, "video", token, use_temp=True)
        
        # Check if creation was successful
        if temp_url.startswith("Error"):
            return temp_url
        
        video_html = (
            f'<video controls autoplay muted loop playsinline '
            f'style="max-width: 100%; height: auto; border-radius: 8px; margin: 10px 0; display: block;" '
            f'onloadstart="this.style.backgroundColor=\'#f0f0f0\'" '
            f'onerror="this.style.display=\'none\'; console.error(\'Video failed to load\')">'
            f'<source src="{temp_url}" type="video/mp4" />'
            f'<p style="text-align: center; color: #666;">Your browser does not support the video tag.</p>'
            f'</video>'
        )
        
        print(f"[Video2Video] Successfully generated video HTML tag with temporary URL: {temp_url}")
        
        # Validate the generated video HTML
        if not validate_video_html(video_html):
            print("[Video2Video] Generated video HTML failed validation")
            return "Error: Generated video HTML is malformed"
        
        return video_html
        
    except Exception as e:
        import traceback
        print("[Video2Video] Exception during generation:")
        traceback.print_exc()
        print(f"Video-to-video generation error: {str(e)}")
        return f"Error generating video (video-to-video): {str(e)}"

def generate_music_from_text(prompt: str, music_length_ms: int = 30000, session_id: Optional[str] = None, token: gr.OAuthToken | None = None) -> str:
    """Generate music from a text prompt using ElevenLabs Music API and return an HTML <audio> tag.

    Returns compressed data URI for deployment compatibility.
    Requires ELEVENLABS_API_KEY in the environment.
    """
    try:
        api_key = os.getenv('ELEVENLABS_API_KEY')
        if not api_key:
            return "Error: ELEVENLABS_API_KEY environment variable is not set."

        headers = {
            'Content-Type': 'application/json',
            'xi-api-key': api_key,
        }
        payload = {
            'prompt': (prompt or 'Epic orchestral theme with soaring strings and powerful brass'),
            'music_length_ms': int(music_length_ms) if music_length_ms else 30000,
        }

        resp = requests.post('https://api.elevenlabs.io/v1/music/compose', headers=headers, json=payload)
        try:
            resp.raise_for_status()
        except Exception as e:
            return f"Error generating music: {getattr(e, 'response', resp).text if hasattr(e, 'response') else resp.text}"

        # Create temporary URL for preview (will be uploaded to HF during deploy)
        filename = "generated_music.mp3"
        temp_url = upload_media_to_hf(resp.content, filename, "audio", token, use_temp=True)
        
        # Check if creation was successful
        if temp_url.startswith("Error"):
            return temp_url
        
        audio_html = (
            "<div class=\"anycoder-music\" style=\"max-width:420px;margin:16px auto;padding:12px 16px;border:1px solid #e5e7eb;border-radius:12px;background:linear-gradient(180deg,#fafafa,#f3f4f6);box-shadow:0 2px 8px rgba(0,0,0,0.06)\">"
            "  <div style=\"font-size:13px;color:#374151;margin-bottom:8px;display:flex;align-items:center;gap:6px\">"
            "    <span>🎵 Generated music</span>"
            "  </div>"
            f"  <audio controls autoplay loop style=\"width:100%;outline:none;\">"
            f"    <source src=\"{temp_url}\" type=\"audio/mpeg\" />"
            "    Your browser does not support the audio element."
            "  </audio>"
            "</div>"
        )
        
        print(f"[Music] Successfully generated music HTML tag with temporary URL: {temp_url}")
        return audio_html
    except Exception as e:
        return f"Error generating music: {str(e)}"

class WanAnimateApp:
    """Wan2.2-Animate integration for character animation and video replacement using DashScope API"""
    
    def __init__(self):
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        if self.api_key:
            dashscope.api_key = self.api_key
        self.url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/image2video/video-synthesis/"
        self.get_url = "https://dashscope.aliyuncs.com/api/v1/tasks"

    def check_task_status(self, task_id: str):
        """Check the status of a specific animation task by TaskId"""
        if not self.api_key:
            return None, "Error: DASHSCOPE_API_KEY environment variable is not set"
            
        try:
            get_url = f"{self.get_url}/{task_id}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(get_url, headers=headers, timeout=30)
            if response.status_code != 200:
                error_msg = f"Failed to get task status: {response.status_code}: {response.text}"
                return None, error_msg
            
            result = response.json()
            task_status = result.get("output", {}).get("task_status")
            
            if task_status == "SUCCEEDED":
                video_url = result["output"]["results"]["video_url"]
                return video_url, "SUCCEEDED"
            elif task_status == "FAILED":
                error_msg = result.get("output", {}).get("message", "Unknown error")
                code_msg = result.get("output", {}).get("code", "Unknown code")
                return None, f"Task failed: {error_msg} Code: {code_msg}"
            else:
                return None, f"Task is still {task_status}"
                
        except Exception as e:
            return None, f"Exception checking task status: {str(e)}"

    def predict(self, ref_img, video, model_id, model):
        """
        Generate animated video using Wan2.2-Animate
        
        Args:
            ref_img: Reference image file path
            video: Template video file path  
            model_id: Animation mode ("wan2.2-animate-move" or "wan2.2-animate-mix")
            model: Inference quality ("wan-pro" or "wan-std")
            
        Returns:
            Tuple of (video_url, status_message)
        """
        if not self.api_key:
            return None, "Error: DASHSCOPE_API_KEY environment variable is not set"
            
        try:
            # Upload files to OSS if needed and get URLs
            _, image_url = check_and_upload_local(model_id, ref_img, self.api_key)
            _, video_url = check_and_upload_local(model_id, video, self.api_key)

            # Prepare the request payload
            payload = {
                "model": model_id,
                "input": {
                    "image_url": image_url,
                    "video_url": video_url
                },
                "parameters": {
                    "check_image": True,
                    "mode": model,
                }
            }
            
            # Set up headers
            headers = {
                "X-DashScope-Async": "enable",
                "X-DashScope-OssResourceResolve": "enable",
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Make the initial API request
            response = requests.post(self.url, json=payload, headers=headers)
            
            # Check if request was successful
            if response.status_code != 200:
                error_msg = f"Initial request failed with status code {response.status_code}: {response.text}"
                print(f"[WanAnimate] {error_msg}")
                return None, error_msg
            
            # Get the task ID from response
            result = response.json()
            task_id = result.get("output", {}).get("task_id")
            if not task_id:
                error_msg = "Failed to get task ID from response"
                print(f"[WanAnimate] {error_msg}")
                return None, error_msg
            
            # Poll for results
            get_url = f"{self.get_url}/{task_id}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            max_attempts = 180  # 15 minutes max wait time (increased from 5 minutes)
            attempt = 0
            
            while attempt < max_attempts:
                try:
                    response = requests.get(get_url, headers=headers, timeout=30)
                    if response.status_code != 200:
                        error_msg = f"Failed to get task status: {response.status_code}: {response.text}"
                        print(f"[WanAnimate] {error_msg}")
                        return None, error_msg
                    
                    result = response.json()
                    task_status = result.get("output", {}).get("task_status")
                    
                    # Log progress every 20 attempts (100 seconds) to show activity
                    if attempt % 20 == 0 or task_status in ["SUCCEEDED", "FAILED"]:
                        print(f"[WanAnimate] Task status check {attempt + 1}/{max_attempts}: {task_status} (TaskId: {task_id})")
                    
                    if task_status == "SUCCEEDED":
                        # Task completed successfully, return video URL
                        video_url = result["output"]["results"]["video_url"]
                        print(f"[WanAnimate] Animation completed successfully: {video_url}")
                        return video_url, "SUCCEEDED"
                    elif task_status == "FAILED":
                        # Task failed, return error message
                        error_msg = result.get("output", {}).get("message", "Unknown error")
                        code_msg = result.get("output", {}).get("code", "Unknown code")
                        full_error = f"Task failed: {error_msg} Code: {code_msg} TaskId: {task_id}"
                        print(f"[WanAnimate] {full_error}")
                        return None, full_error
                    else:
                        # Task is still running, wait and retry
                        time.sleep(5)  # Wait 5 seconds before polling again
                        attempt += 1
                        
                except requests.exceptions.RequestException as e:
                    print(f"[WanAnimate] Network error during status check {attempt + 1}: {str(e)}")
                    # For network errors, wait a bit longer before retrying
                    time.sleep(10)
                    attempt += 1
                    continue
            
            # Timeout reached
            timeout_msg = f"Animation generation timed out after {max_attempts * 5} seconds ({max_attempts * 5 // 60} minutes). TaskId: {task_id}. The animation may still be processing - please check back later or try with a simpler input."
            print(f"[WanAnimate] {timeout_msg}")
            return None, timeout_msg
            
        except Exception as e:
            error_msg = f"Exception during animation generation: {str(e)}"
            print(f"[WanAnimate] {error_msg}")
            return None, error_msg

def generate_animation_from_image_video(input_image_data, input_video_data, prompt: str, model_id: str = "wan2.2-animate-move", model: str = "wan-pro", session_id: Optional[str] = None, token: gr.OAuthToken | None = None) -> str:
    """Generate animated video from reference image and template video using Wan2.2-Animate.
    
    Returns an HTML <video> tag whose source points to a temporary file URL.
    """
    try:
        print(f"[ImageVideo2Animation] Starting animation generation with model={model_id}, quality={model}")
        
        if not os.getenv("DASHSCOPE_API_KEY"):
            print("[ImageVideo2Animation] Missing DASHSCOPE_API_KEY")
            return "Error: DASHSCOPE_API_KEY environment variable is not set. Please configure your DashScope API key."

        # Normalize inputs to file paths
        def _save_to_temp_file(data, suffix):
            if isinstance(data, str) and os.path.exists(data):
                return data
            elif hasattr(data, 'name') and os.path.exists(data.name):
                return data.name
            else:
                # Save to temporary file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                if hasattr(data, 'read'):
                    temp_file.write(data.read())
                elif isinstance(data, (bytes, bytearray)):
                    temp_file.write(data)
                elif isinstance(data, np.ndarray):
                    # Handle numpy array (likely image data)
                    if suffix.lower() in ['.jpg', '.jpeg', '.png']:
                        # Convert numpy array to image
                        from PIL import Image
                        if data.dtype != np.uint8:
                            data = (data * 255).astype(np.uint8)
                        if len(data.shape) == 3 and data.shape[2] == 3:
                            # RGB image
                            img = Image.fromarray(data, 'RGB')
                        elif len(data.shape) == 3 and data.shape[2] == 4:
                            # RGBA image
                            img = Image.fromarray(data, 'RGBA')
                        elif len(data.shape) == 2:
                            # Grayscale image
                            img = Image.fromarray(data, 'L')
                        else:
                            raise ValueError(f"Unsupported numpy array shape for image: {data.shape}")
                        img.save(temp_file.name, format='JPEG' if suffix.lower() in ['.jpg', '.jpeg'] else 'PNG')
                    else:
                        raise ValueError(f"Cannot save numpy array as {suffix} format")
                else:
                    raise ValueError(f"Unsupported data type: {type(data)}")
                temp_file.close()
                return temp_file.name

        ref_img_path = _save_to_temp_file(input_image_data, '.jpg')
        video_path = _save_to_temp_file(input_video_data, '.mp4')
        
        print(f"[ImageVideo2Animation] Input files prepared: image={ref_img_path}, video={video_path}")

        # Initialize WanAnimateApp and generate animation
        wan_app = WanAnimateApp()
        video_url, status = wan_app.predict(ref_img_path, video_path, model_id, model)
        
        if video_url and status == "SUCCEEDED":
            print(f"[ImageVideo2Animation] Animation generated successfully: {video_url}")
            
            # Download the video and create temporary URL
            try:
                response = requests.get(video_url, timeout=60)
                response.raise_for_status()
                video_bytes = response.content
                
                filename = "wan_animate_result.mp4"
                temp_url = upload_media_to_hf(video_bytes, filename, "video", token, use_temp=True)
                
                if temp_url.startswith("Error"):
                    print(f"[ImageVideo2Animation] Failed to upload video: {temp_url}")
                    return temp_url
                
                # Create video HTML tag
                video_html = (
                    f'<video controls autoplay muted loop playsinline '
                    f'style="max-width:100%; height:auto; border-radius:8px; box-shadow:0 4px 8px rgba(0,0,0,0.1)" '
                    f'onerror="this.style.display=\'none\'; console.error(\'Animation video failed to load\')">'
                    f'<source src="{temp_url}" type="video/mp4" />'
                    f'<p style="text-align: center; color: #666;">Your browser does not support the video tag.</p>'
                    f'</video>'
                )
                
                print(f"[ImageVideo2Animation] Successfully created animation HTML with temporary URL: {temp_url}")
                return video_html
                
            except Exception as e:
                error_msg = f"Failed to download generated animation: {str(e)}"
                print(f"[ImageVideo2Animation] {error_msg}")
                return f"Error: {error_msg}"
        else:
            # Provide more helpful error messages based on status
            if "timed out" in str(status).lower():
                error_msg = f"Animation generation timed out. This can happen with complex animations or during high server load. Please try again with simpler inputs or wait a few minutes before retrying. Details: {status}"
            elif "taskid" in str(status).lower():
                error_msg = f"Animation generation failed. You can check the status later using the TaskId from the error message. Details: {status}"
            else:
                error_msg = f"Animation generation failed: {status}"
            print(f"[ImageVideo2Animation] {error_msg}")
            return f"Error: {error_msg}"
            
    except Exception as e:
        print(f"[ImageVideo2Animation] Exception during generation:")
        print(f"Animation generation error: {str(e)}")
        return f"Error generating animation: {str(e)}"

def extract_image_prompts_from_text(text: str, num_images_needed: int = 1) -> list:
    """Extract image generation prompts from the full text based on number of images needed"""
    # Use the entire text as the base prompt for image generation
    # Clean up the text and create variations for the required number of images
    
    # Clean the text
    cleaned_text = text.strip()
    if not cleaned_text:
        return []
    
    # Create variations of the prompt for the required number of images
    prompts = []
    
    # Generate exactly the number of images needed
    for i in range(num_images_needed):
        if i == 0:
            # First image: Use the full prompt as-is
            prompts.append(cleaned_text)
        elif i == 1:
            # Second image: Add "visual representation" to make it more image-focused
            prompts.append(f"Visual representation of {cleaned_text}")
        elif i == 2:
            # Third image: Add "illustration" to create a different style
            prompts.append(f"Illustration of {cleaned_text}")
        else:
            # For additional images, use different variations
            variations = [
                f"Digital art of {cleaned_text}",
                f"Modern design of {cleaned_text}",
                f"Professional illustration of {cleaned_text}",
                f"Clean design of {cleaned_text}",
                f"Beautiful visualization of {cleaned_text}",
                f"Stylish representation of {cleaned_text}",
                f"Contemporary design of {cleaned_text}",
                f"Elegant illustration of {cleaned_text}"
            ]
            variation_index = (i - 3) % len(variations)
            prompts.append(variations[variation_index])
    
    return prompts

def create_image_replacement_blocks(html_content: str, user_prompt: str) -> str:
    """Create search/replace blocks to replace placeholder images with generated Qwen images"""
    if not user_prompt:
        return ""
    
    # Find existing image placeholders in the HTML first
    import re
    
    # Common patterns for placeholder images
    placeholder_patterns = [
        r'<img[^>]*src=["\'](?:placeholder|dummy|sample|example)[^"\']*["\'][^>]*>',
        r'<img[^>]*src=["\']https?://via\.placeholder\.com[^"\']*["\'][^>]*>',
        r'<img[^>]*src=["\']https?://picsum\.photos[^"\']*["\'][^>]*>',
        r'<img[^>]*src=["\']https?://dummyimage\.com[^"\']*["\'][^>]*>',
        r'<img[^>]*alt=["\'][^"\']*placeholder[^"\']*["\'][^>]*>',
        r'<img[^>]*class=["\'][^"\']*placeholder[^"\']*["\'][^>]*>',
        r'<img[^>]*id=["\'][^"\']*placeholder[^"\']*["\'][^>]*>',
        r'<img[^>]*src=["\']data:image[^"\']*["\'][^>]*>',  # Base64 images
        r'<img[^>]*src=["\']#["\'][^>]*>',  # Empty src
        r'<img[^>]*src=["\']about:blank["\'][^>]*>',  # About blank
    ]
    
    # Find all placeholder images
    placeholder_images = []
    for pattern in placeholder_patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        placeholder_images.extend(matches)
    
    # Filter out HF URLs from placeholders (they are real generated content)
    placeholder_images = [img for img in placeholder_images if 'huggingface.co/datasets/' not in img]
    
    # If no placeholder images found, look for any img tags
    if not placeholder_images:
        img_pattern = r'<img[^>]*>'
        # Case-insensitive to catch <IMG> or mixed-case tags
        placeholder_images = re.findall(img_pattern, html_content, re.IGNORECASE)
    
    # Also look for div elements that might be image placeholders
    div_placeholder_patterns = [
        r'<div[^>]*class=["\'][^"\']*(?:image|img|photo|picture)[^"\']*["\'][^>]*>.*?</div>',
        r'<div[^>]*id=["\'][^"\']*(?:image|img|photo|picture)[^"\']*["\'][^>]*>.*?</div>',
    ]
    
    for pattern in div_placeholder_patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
        placeholder_images.extend(matches)
    
    # Count how many images we need to generate
    num_images_needed = len(placeholder_images)
    
    if num_images_needed == 0:
        return ""
    
    # Generate image prompts based on the number of images found
    image_prompts = extract_image_prompts_from_text(user_prompt, num_images_needed)
    
    # Generate images for each prompt
    generated_images = []
    for i, prompt in enumerate(image_prompts):
        image_html = generate_image_with_hunyuan(prompt, i, token=None)  # TODO: Pass token from parent context
        if not image_html.startswith("Error"):
            generated_images.append((i, image_html))
    
    if not generated_images:
        return ""
    
    # Create search/replace blocks
    replacement_blocks = []
    
    for i, (prompt_index, generated_image) in enumerate(generated_images):
        if i < len(placeholder_images):
            # Replace existing placeholder
            placeholder = placeholder_images[i]
            # Clean up the placeholder for better matching
            placeholder_clean = re.sub(r'\s+', ' ', placeholder.strip())
            
            # Try multiple variations of the placeholder for better matching
            placeholder_variations = [
                placeholder_clean,
                placeholder_clean.replace('"', "'"),
                placeholder_clean.replace("'", '"'),
                re.sub(r'\s+', ' ', placeholder_clean),
                placeholder_clean.replace('  ', ' '),
            ]
            
            # Create a replacement block for each variation
            for variation in placeholder_variations:
                replacement_blocks.append(f"""{SEARCH_START}
{variation}
{DIVIDER}
{generated_image}
{REPLACE_END}""")
        else:
            # Add new image if we have more generated images than placeholders
            # Find a good insertion point (after body tag or main content)
            if '<body' in html_content:
                body_end = html_content.find('>', html_content.find('<body')) + 1
                insertion_point = html_content[:body_end] + '\n    '
                replacement_blocks.append(f"""{SEARCH_START}
{insertion_point}
{DIVIDER}
{insertion_point}
    {generated_image}
{REPLACE_END}""")
    
    return '\n\n'.join(replacement_blocks)

def create_image_replacement_blocks_text_to_image_single(html_content: str, prompt: str) -> str:
    """Create search/replace blocks that generate and insert ONLY ONE text-to-image result.

    Replaces the first detected placeholder; if none found, inserts one image near the top of <body>.
    """
    if not prompt or not prompt.strip():
        return ""

    import re

    # Detect placeholders similarly to the multi-image version
    placeholder_patterns = [
        r'<img[^>]*src=["\'](?:placeholder|dummy|sample|example)[^"\']*["\'][^>]*>',
        r'<img[^>]*src=["\']https?://via\.placeholder\.com[^"\']*["\'][^>]*>',
        r'<img[^>]*src=["\']https?://picsum\.photos[^"\']*["\'][^>]*>',
        r'<img[^>]*src=["\']https?://dummyimage\.com[^"\']*["\'][^>]*>',
        r'<img[^>]*alt=["\'][^"\']*placeholder[^"\']*["\'][^>]*>',
        r'<img[^>]*class=["\'][^"\']*placeholder[^"\']*["\'][^>]*>',
        r'<img[^>]*id=["\'][^"\']*placeholder[^"\']*["\'][^>]*>',
        r'<img[^>]*src=["\']data:image[^"\']*["\'][^>]*>',
        r'<img[^>]*src=["\']#["\'][^>]*>',
        r'<img[^>]*src=["\']about:blank["\'][^>]*>',
    ]

    placeholder_images = []
    for pattern in placeholder_patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        if matches:
            placeholder_images.extend(matches)
    
    # Filter out HF URLs from placeholders (they are real generated content)
    placeholder_images = [img for img in placeholder_images if 'huggingface.co/datasets/' not in img]
    
    # Filter out HF URLs from placeholders (they are real generated content)
    placeholder_images = [img for img in placeholder_images if 'huggingface.co/datasets/' not in img]

    # Fallback to any <img> if no placeholders
    if not placeholder_images:
        img_pattern = r'<img[^>]*>'
        placeholder_images = re.findall(img_pattern, html_content)

    # Generate a single image
    image_html = generate_image_with_hunyuan(prompt, 0, token=None)  # TODO: Pass token from parent context
    if image_html.startswith("Error"):
        return ""

    # Replace first placeholder if present
    if placeholder_images:
        placeholder = placeholder_images[0]
        placeholder_clean = re.sub(r'\s+', ' ', placeholder.strip())
        placeholder_variations = [
            placeholder_clean,
            placeholder_clean.replace('"', "'"),
            placeholder_clean.replace("'", '"'),
            re.sub(r'\s+', ' ', placeholder_clean),
            placeholder_clean.replace('  ', ' '),
        ]
        blocks = []
        for variation in placeholder_variations:
            blocks.append(f"""{SEARCH_START}
{variation}
{DIVIDER}
{image_html}
{REPLACE_END}""")
        return '\n\n'.join(blocks)

    # Otherwise insert after <body>
    if '<body' in html_content:
        body_end = html_content.find('>', html_content.find('<body')) + 1
        insertion_point = html_content[:body_end] + '\n    '
        return f"""{SEARCH_START}
{insertion_point}
{DIVIDER}
{insertion_point}
    {image_html}
{REPLACE_END}"""

    # If no <body>, just append
    return f"{SEARCH_START}\n\n{DIVIDER}\n{image_html}\n{REPLACE_END}"

def create_video_replacement_blocks_text_to_video(html_content: str, prompt: str, session_id: Optional[str] = None) -> str:
    """Create search/replace blocks that generate and insert ONLY ONE text-to-video result.

    Replaces the first detected <img> placeholder; if none found, inserts one video near the top of <body>.
    """
    if not prompt or not prompt.strip():
        return ""

    import re

    # Detect the same placeholders as image counterparts, to replace the first image slot with a video
    placeholder_patterns = [
        r'<img[^>]*src=["\'](?:placeholder|dummy|sample|example)[^"\']*["\'][^>]*>',
        r'<img[^>]*src=["\']https?://via\.placeholder\.com[^"\']*["\'][^>]*>',
        r'<img[^>]*src=["\']https?://picsum\.photos[^"\']*["\'][^>]*>',
        r'<img[^>]*src=["\']https?://dummyimage\.com[^"\']*["\'][^>]*>',
        r'<img[^>]*alt=["\'][^"\']*placeholder[^"\']*["\'][^>]*>',
        r'<img[^>]*class=["\'][^"\']*placeholder[^"\']*["\'][^>]*>',
        r'<img[^>]*id=["\'][^"\']*placeholder[^"\']*["\'][^>]*>',
        r'<img[^>]*src=["\']data:image[^"\']*["\'][^>]*>',
        r'<img[^>]*src=["\']#["\'][^>]*>',
        r'<img[^>]*src=["\']about:blank["\'][^>]*>',
    ]

    placeholder_images = []
    for pattern in placeholder_patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        if matches:
            placeholder_images.extend(matches)
    
    # Filter out HF URLs from placeholders (they are real generated content)
    placeholder_images = [img for img in placeholder_images if 'huggingface.co/datasets/' not in img]

    if not placeholder_images:
        img_pattern = r'<img[^>]*>'
        placeholder_images = re.findall(img_pattern, html_content)

    video_html = generate_video_from_text(prompt, session_id=session_id, token=None)  # TODO: Pass token from parent context
    if video_html.startswith("Error"):
        return ""

    # Replace first placeholder if present
    if placeholder_images:
        placeholder = placeholder_images[0]
        placeholder_clean = re.sub(r'\s+', ' ', placeholder.strip())
        placeholder_variations = [
            placeholder,
            placeholder_clean,
            placeholder_clean.replace('"', "'"),
            placeholder_clean.replace("'", '"'),
            re.sub(r'\s+', ' ', placeholder_clean),
            placeholder_clean.replace('  ', ' '),
        ]
        blocks = []
        for variation in placeholder_variations:
            blocks.append(f"""{SEARCH_START}
{variation}
{DIVIDER}
{video_html}
{REPLACE_END}""")
        return '\n\n'.join(blocks)

    # Otherwise insert after <body> with proper container
    if '<body' in html_content:
        body_start = html_content.find('<body')
        body_end = html_content.find('>', body_start) + 1
        opening_body_tag = html_content[body_start:body_end]
        
        # Look for existing container elements to insert into
        body_content_start = body_end
        
        # Try to find a good insertion point within existing content structure
        patterns_to_try = [
            r'<main[^>]*>',
            r'<section[^>]*class="[^"]*hero[^"]*"[^>]*>',
            r'<div[^>]*class="[^"]*container[^"]*"[^>]*>',
            r'<header[^>]*>',
        ]
        
        insertion_point = None
        for pattern in patterns_to_try:
            import re
            match = re.search(pattern, html_content[body_content_start:], re.IGNORECASE)
            if match:
                match_end = body_content_start + match.end()
                # Find the end of this tag
                tag_content = html_content[body_content_start + match.start():match_end]
                insertion_point = html_content[:match_end] + '\n        '
                break
        
        if not insertion_point:
            # Fallback to right after body tag with container div
            insertion_point = html_content[:body_end] + '\n    '
            video_with_container = f'<div class="video-container" style="margin: 20px 0; text-align: center;">\n        {video_html}\n    </div>'
            return f"""{SEARCH_START}
{insertion_point}
{DIVIDER}
{insertion_point}
    {video_with_container}
{REPLACE_END}"""
        else:
            return f"""{SEARCH_START}
{insertion_point}
{DIVIDER}
{insertion_point}
        {video_html}
{REPLACE_END}"""

    # If no <body>, just append
    return f"{SEARCH_START}\n\n{DIVIDER}\n{video_html}\n{REPLACE_END}"

def create_music_replacement_blocks_text_to_music(html_content: str, prompt: str, session_id: Optional[str] = None) -> str:
    """Create search/replace blocks that insert ONE generated <audio> near the top of <body>.

    Unlike images/videos which replace placeholders, music doesn't map to an <img> tag.
    We simply insert an <audio> player after the opening <body>.
    """
    if not prompt or not prompt.strip():
        return ""

    audio_html = generate_music_from_text(prompt, session_id=session_id, token=None)  # TODO: Pass token from parent context
    if audio_html.startswith("Error"):
        return ""

    # Prefer inserting after the first <section>...</section> if present; else after <body>
    import re
    section_match = re.search(r"<section\b[\s\S]*?</section>", html_content, flags=re.IGNORECASE)
    if section_match:
        section_html = section_match.group(0)
        section_clean = re.sub(r"\s+", " ", section_html.strip())
        variations = [
            section_html,
            section_clean,
            section_clean.replace('"', "'"),
            section_clean.replace("'", '"'),
            re.sub(r"\s+", " ", section_clean),
        ]
        blocks = []
        for v in variations:
            blocks.append(f"""{SEARCH_START}
{v}
{DIVIDER}
{v}\n    {audio_html}
{REPLACE_END}""")
        return "\n\n".join(blocks)
    if '<body' in html_content:
        body_end = html_content.find('>', html_content.find('<body')) + 1
        insertion_point = html_content[:body_end] + '\n    '
        return f"""{SEARCH_START}
{insertion_point}
{DIVIDER}
{insertion_point}
    {audio_html}
{REPLACE_END}"""

    # If no <body>, just append
    return f"{SEARCH_START}\n\n{DIVIDER}\n{audio_html}\n{REPLACE_END}"
def create_image_replacement_blocks_from_input_image(html_content: str, user_prompt: str, input_image_data, max_images: int = 1) -> str:
    """Create search/replace blocks using image-to-image generation with a provided input image.

    Mirrors placeholder detection from create_image_replacement_blocks but uses generate_image_to_image.
    """
    if not user_prompt:
        return ""

    import re

    placeholder_patterns = [
        r'<img[^>]*src=["\'](?:placeholder|dummy|sample|example)[^"\']*["\'][^>]*>',
        r'<img[^>]*src=["\']https?://via\.placeholder\.com[^"\']*["\'][^>]*>',
        r'<img[^>]*src=["\']https?://picsum\.photos[^"\']*["\'][^>]*>',
        r'<img[^>]*src=["\']https?://dummyimage\.com[^"\']*["\'][^>]*>',
        r'<img[^>]*alt=["\'][^"\']*placeholder[^"\']*["\'][^>]*>',
        r'<img[^>]*class=["\'][^"\']*placeholder[^"\']*["\'][^>]*>',
        r'<img[^>]*id=["\'][^"\']*placeholder[^"\']*["\'][^>]*>',
        r'<img[^>]*src=["\']data:image[^"\']*["\'][^>]*>',
        r'<img[^>]*src=["\']#["\'][^>]*>',
        r'<img[^>]*src=["\']about:blank["\'][^>]*>',
    ]

    placeholder_images = []
    for pattern in placeholder_patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        placeholder_images.extend(matches)
    
    # Filter out HF URLs from placeholders (they are real generated content)
    placeholder_images = [img for img in placeholder_images if 'huggingface.co/datasets/' not in img]

    if not placeholder_images:
        img_pattern = r'<img[^>]*>'
        placeholder_images = re.findall(img_pattern, html_content)
        # Filter HF URLs from fallback images too
        placeholder_images = [img for img in placeholder_images if 'huggingface.co/datasets/' not in img]

    div_placeholder_patterns = [
        r'<div[^>]*class=["\'][^"\']*(?:image|img|photo|picture)[^"\']*["\'][^>]*>.*?</div>',
        r'<div[^>]*id=["\'][^"\']*(?:image|img|photo|picture)[^"\']*["\'][^>]*>.*?</div>',
    ]
    for pattern in div_placeholder_patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
        placeholder_images.extend(matches)

    num_images_needed = len(placeholder_images)
    num_to_replace = min(num_images_needed, max(0, int(max_images)))
    if num_images_needed == 0:
        # No placeholders; generate one image to append (only if at least one upload is present)
        if num_to_replace <= 0:
            return ""
        prompts = extract_image_prompts_from_text(user_prompt, 1)
        if not prompts:
            return ""
        image_html = generate_image_to_image(input_image_data, prompts[0], token=None)  # TODO: Pass token from parent context
        if image_html.startswith("Error"):
            return ""
        return f"{SEARCH_START}\n\n{DIVIDER}\n<div class=\"generated-images\">{image_html}</div>\n{REPLACE_END}"

    if num_to_replace <= 0:
        return ""
    image_prompts = extract_image_prompts_from_text(user_prompt, num_to_replace)

    generated_images = []
    for i, prompt in enumerate(image_prompts):
        image_html = generate_image_to_image(input_image_data, prompt, token=None)  # TODO: Pass token from parent context
        if not image_html.startswith("Error"):
            generated_images.append((i, image_html))

    if not generated_images:
        return ""

    replacement_blocks = []
    for i, (prompt_index, generated_image) in enumerate(generated_images):
        if i < num_to_replace and i < len(placeholder_images):
            placeholder = placeholder_images[i]
            placeholder_clean = re.sub(r'\s+', ' ', placeholder.strip())
            placeholder_variations = [
                placeholder_clean,
                placeholder_clean.replace('"', "'"),
                placeholder_clean.replace("'", '"'),
                re.sub(r'\s+', ' ', placeholder_clean),
                placeholder_clean.replace('  ', ' '),
            ]
            for variation in placeholder_variations:
                replacement_blocks.append(f"""{SEARCH_START}
{variation}
{DIVIDER}
{generated_image}
{REPLACE_END}""")
        # Do not insert additional images beyond the uploaded count

    return '\n\n'.join(replacement_blocks)

def create_video_replacement_blocks_from_input_image(html_content: str, user_prompt: str, input_image_data, session_id: Optional[str] = None) -> str:
    """Create search/replace blocks that replace the first <img> (or placeholder) with a generated <video>.

    Uses generate_video_from_image to produce a single video and swaps it in.
    """
    if not user_prompt:
        return ""

    import re
    print("[Image2Video] Creating replacement blocks for video insertion")

    placeholder_patterns = [
        r'<img[^>]*src=["\'](?:placeholder|dummy|sample|example)[^"\']*["\'][^>]*>',
        r'<img[^>]*src=["\']https?://via\.placeholder\.com[^"\']*["\'][^>]*>',
        r'<img[^>]*src=["\']https?://picsum\.photos[^"\']*["\'][^>]*>',
        r'<img[^>]*src=["\']https?://dummyimage\.com[^"\']*["\'][^>]*>',
        r'<img[^>]*alt=["\'][^"\']*placeholder[^"\']*["\'][^>]*>',
        r'<img[^>]*class=["\'][^"\']*placeholder[^"\']*["\'][^>]*>',
        r'<img[^>]*id=["\'][^"\']*placeholder[^"\']*["\'][^>]*>',
        r'<img[^>]*src=["\']data:image[^"\']*["\'][^>]*>',
        r'<img[^>]*src=["\']#["\'][^>]*>',
        r'<img[^>]*src=["\']about:blank["\'][^>]*>',
    ]

    placeholder_images = []
    for pattern in placeholder_patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        if matches:
            placeholder_images.extend(matches)
    
    # Filter out HF URLs from placeholders (they are real generated content)
    placeholder_images = [img for img in placeholder_images if 'huggingface.co/datasets/' not in img]

    if not placeholder_images:
        img_pattern = r'<img[^>]*>'
        placeholder_images = re.findall(img_pattern, html_content)
    print(f"[Image2Video] Found {len(placeholder_images)} candidate <img> elements")

    video_html = generate_video_from_image(input_image_data, user_prompt, session_id=session_id, token=None)  # TODO: Pass token from parent context
    try:
        has_file_src = 'src="' in video_html and video_html.count('src="') >= 1 and 'data:video/mp4;base64' not in video_html.split('src="', 1)[1]
        print(f"[Image2Video] Generated video HTML length={len(video_html)}; has_file_src={has_file_src}")
    except Exception:
        pass
    if video_html.startswith("Error"):
        print("[Image2Video] Video generation returned error; aborting replacement")
        return ""

    if placeholder_images:
        placeholder = placeholder_images[0]
        placeholder_clean = re.sub(r'\s+', ' ', placeholder.strip())
        print("[Image2Video] Replacing first image placeholder with video")
        placeholder_variations = [
            # Try the exact string first to maximize replacement success
            placeholder,
            placeholder_clean,
            placeholder_clean.replace('"', "'"),
            placeholder_clean.replace("'", '"'),
            re.sub(r'\s+', ' ', placeholder_clean),
            placeholder_clean.replace('  ', ' '),
        ]
        blocks = []
        for variation in placeholder_variations:
            blocks.append(f"""{SEARCH_START}
{variation}
{DIVIDER}
{video_html}
{REPLACE_END}""")
        return '\n\n'.join(blocks)

    if '<body' in html_content:
        body_start = html_content.find('<body')
        body_end = html_content.find('>', body_start) + 1
        opening_body_tag = html_content[body_start:body_end]
        print("[Image2Video] No <img> found; inserting video right after the opening <body> tag")
        print(f"[Image2Video] Opening <body> tag snippet: {opening_body_tag[:120]}")
        return f"""{SEARCH_START}
{opening_body_tag}
{DIVIDER}
{opening_body_tag}
    {video_html}
{REPLACE_END}"""

    print("[Image2Video] No <body> tag; appending video via replacement block")
    return f"{SEARCH_START}\n\n{DIVIDER}\n{video_html}\n{REPLACE_END}"

def create_video_replacement_blocks_from_input_video(html_content: str, user_prompt: str, input_video_data, session_id: Optional[str] = None) -> str:
    """Create search/replace blocks that replace the first <video> (or placeholder) with a generated <video>.

    Uses generate_video_from_video to produce a single video and swaps it in.
    """
    if not user_prompt:
        return ""

    import re
    print("[Video2Video] Creating replacement blocks for video replacement")

    # Look for existing video elements first
    video_patterns = [
        r'<video[^>]*>.*?</video>',
        r'<video[^>]*/>',
        r'<video[^>]*></video>',
    ]

    placeholder_videos = []
    for pattern in video_patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
        if matches:
            placeholder_videos.extend(matches)
    
    # If no videos found, look for video placeholders or divs that might represent videos
    if not placeholder_videos:
        placeholder_patterns = [
            r'<div[^>]*class=["\'][^"\']*video[^"\']*["\'][^>]*>.*?</div>',
            r'<div[^>]*id=["\'][^"\']*video[^"\']*["\'][^>]*>.*?</div>',
            r'<iframe[^>]*src=["\'][^"\']*youtube[^"\']*["\'][^>]*>.*?</iframe>',
            r'<iframe[^>]*src=["\'][^"\']*vimeo[^"\']*["\'][^>]*>.*?</iframe>',
        ]
        for pattern in placeholder_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
            if matches:
                placeholder_videos.extend(matches)

    print(f"[Video2Video] Found {len(placeholder_videos)} candidate video elements")

    video_html = generate_video_from_video(input_video_data, user_prompt, session_id=session_id, token=None)
    try:
        has_file_src = 'src="' in video_html and video_html.count('src="') >= 1 and 'data:video/mp4;base64' not in video_html.split('src="', 1)[1]
        print(f"[Video2Video] Generated video HTML length={len(video_html)}; has_file_src={has_file_src}")
    except Exception:
        pass
    if video_html.startswith("Error"):
        print("[Video2Video] Video generation returned error; aborting replacement")
        return ""

    if placeholder_videos:
        placeholder = placeholder_videos[0]
        placeholder_clean = re.sub(r'\s+', ' ', placeholder.strip())
        print("[Video2Video] Replacing first video placeholder with generated video")
        placeholder_variations = [
            # Try the exact string first to maximize replacement success
            placeholder,
            placeholder_clean,
            placeholder_clean.replace('"', "'"),
            placeholder_clean.replace("'", '"'),
            re.sub(r'\s+', ' ', placeholder_clean),
            placeholder_clean.replace('  ', ' '),
        ]
        blocks = []
        for variation in placeholder_variations:
            blocks.append(f"""{SEARCH_START}
{variation}
{DIVIDER}
{video_html}
{REPLACE_END}""")
        return '\n\n'.join(blocks)

    if '<body' in html_content:
        body_start = html_content.find('<body')
        body_end = html_content.find('>', body_start) + 1
        opening_body_tag = html_content[body_start:body_end]
        print("[Video2Video] No <video> found; inserting video right after the opening <body> tag")
        print(f"[Video2Video] Opening <body> tag snippet: {opening_body_tag[:120]}")
        return f"""{SEARCH_START}
{opening_body_tag}
{DIVIDER}
{opening_body_tag}
    {video_html}
{REPLACE_END}"""

    print("[Video2Video] No <body> tag; appending video via replacement block")
    return f"{SEARCH_START}\n\n{DIVIDER}\n{video_html}\n{REPLACE_END}"

def apply_generated_media_to_html(html_content: str, user_prompt: str, enable_text_to_image: bool, enable_image_to_image: bool, input_image_data, image_to_image_prompt: str | None = None, text_to_image_prompt: str | None = None, enable_image_to_video: bool = False, image_to_video_prompt: str | None = None, session_id: Optional[str] = None, enable_text_to_video: bool = False, text_to_video_prompt: Optional[str] = None, enable_video_to_video: bool = False, video_to_video_prompt: Optional[str] = None, input_video_data = None, enable_text_to_music: bool = False, text_to_music_prompt: Optional[str] = None, enable_image_video_to_animation: bool = False, animation_mode: str = "wan2.2-animate-move", animation_quality: str = "wan-pro", animation_video_data = None, token: gr.OAuthToken | None = None) -> str:
    """Apply text/image/video/music replacements to HTML content.

    - Works with single-document HTML strings
    - Also supports multi-page outputs formatted as === filename === sections by
      applying changes to the HTML entrypoint (index.html if present) and
      returning the updated multi-page text.
    """
    # Detect multi-page sections and choose an entry HTML to modify
    is_multipage = False
    multipage_files: Dict[str, str] = {}
    entry_html_path: Optional[str] = None
    try:
        multipage_files = parse_multipage_html_output(html_content) or {}
        if multipage_files:
            is_multipage = True
            if 'index.html' in multipage_files:
                entry_html_path = 'index.html'
            else:
                html_paths = [p for p in multipage_files.keys() if p.lower().endswith('.html')]
                entry_html_path = html_paths[0] if html_paths else None
    except Exception:
        is_multipage = False
        multipage_files = {}
        entry_html_path = None

    result = multipage_files.get(entry_html_path, html_content) if is_multipage and entry_html_path else html_content
    try:
        print(
            f"[MediaApply] enable_i2v={enable_image_to_video}, enable_i2i={enable_image_to_image}, "
            f"enable_t2i={enable_text_to_image}, enable_t2v={enable_text_to_video}, enable_v2v={enable_video_to_video}, enable_t2m={enable_text_to_music}, enable_iv2a={enable_image_video_to_animation}, has_image={input_image_data is not None}, has_video={input_video_data is not None}, has_anim_video={animation_video_data is not None}"
        )
        
        # If image+video-to-animation is enabled, generate animated video and return.
        if enable_image_video_to_animation and input_image_data is not None and animation_video_data is not None and (result.strip().startswith('<!DOCTYPE html>') or result.strip().startswith('<html')):
            print(f"[MediaApply] Running image+video-to-animation with mode={animation_mode}, quality={animation_quality}")
            try:
                animation_html_tag = generate_animation_from_image_video(
                    input_image_data, 
                    animation_video_data, 
                    user_prompt or "", 
                    model_id=animation_mode, 
                    model=animation_quality, 
                    session_id=session_id, 
                    token=token
                )
                if not (animation_html_tag or "").startswith("Error"):
                    # Validate animation video HTML before attempting placement
                    if validate_video_html(animation_html_tag):
                        blocks_anim = llm_place_media(result, animation_html_tag, media_kind="video")
                    else:
                        print("[MediaApply] Generated animation HTML failed validation, skipping LLM placement")
                        blocks_anim = ""
                else:
                    print(f"[MediaApply] Animation generation failed: {animation_html_tag}")
                    blocks_anim = ""
            except Exception as e:
                print(f"[MediaApply] Exception during animation generation: {str(e)}")
                blocks_anim = ""
            
            # If LLM placement failed, use fallback placement
            if not blocks_anim:
                # Create simple replacement block for animation video
                blocks_anim = f"""{SEARCH_START}
</head>

{DIVIDER}
</head>
<div class="animation-container" style="margin: 20px 0; text-align: center;">
    {animation_html_tag}
</div>
{REPLACE_END}"""
            
            if blocks_anim:
                print("[MediaApply] Applying animation replacement blocks")
                result = apply_search_replace_changes(result, blocks_anim)
                if is_multipage and entry_html_path:
                    multipage_files[entry_html_path] = result
                    return format_multipage_output(multipage_files)
                return result

        # If image-to-video is enabled, replace the first image with a generated video and return.
        if enable_image_to_video and input_image_data is not None and (result.strip().startswith('<!DOCTYPE html>') or result.strip().startswith('<html')):
            i2v_prompt = (image_to_video_prompt or user_prompt or "").strip()
            print(f"[MediaApply] Running image-to-video with prompt len={len(i2v_prompt)}")
            try:
                video_html_tag = generate_video_from_image(input_image_data, i2v_prompt, session_id=session_id, token=token)
                if not (video_html_tag or "").startswith("Error"):
                    # Validate video HTML before attempting placement
                    if validate_video_html(video_html_tag):
                        blocks_v = llm_place_media(result, video_html_tag, media_kind="video")
                    else:
                        print("[MediaApply] Generated video HTML failed validation, skipping LLM placement")
                        blocks_v = ""
                else:
                    print(f"[MediaApply] Video generation failed: {video_html_tag}")
                    blocks_v = ""
            except Exception as e:
                print(f"[MediaApply] Exception during image-to-video generation: {str(e)}")
                blocks_v = ""
            if not blocks_v:
                blocks_v = create_video_replacement_blocks_from_input_image(result, i2v_prompt, input_image_data, session_id=session_id)
            if blocks_v:
                print("[MediaApply] Applying image-to-video replacement blocks")
                before_len = len(result)
                result_after = apply_search_replace_changes(result, blocks_v)
                after_len = len(result_after)
                changed = (result_after != result)
                print(f"[MediaApply] i2v blocks length={len(blocks_v)}; html before={before_len}, after={after_len}, changed={changed}")
                if not changed:
                    print("[MediaApply] DEBUG: Replacement did not change content. Dumping first block:")
                    try:
                        first_block = blocks_v.split(REPLACE_END)[0][:1000]
                        print(first_block)
                    except Exception:
                        pass
                result = result_after
            else:
                print("[MediaApply] No i2v replacement blocks generated")
            if is_multipage and entry_html_path:
                multipage_files[entry_html_path] = result
                return format_multipage_output(multipage_files)
            return result

        # If video-to-video is enabled, replace the first video with a generated video and return.
        if enable_video_to_video and input_video_data is not None and (result.strip().startswith('<!DOCTYPE html>') or result.strip().startswith('<html')):
            v2v_prompt = (video_to_video_prompt or user_prompt or "").strip()
            print(f"[MediaApply] Running video-to-video with prompt len={len(v2v_prompt)}")
            try:
                video_html_tag = generate_video_from_video(input_video_data, v2v_prompt, session_id=session_id, token=token)
                if not (video_html_tag or "").startswith("Error"):
                    # Validate video HTML before attempting placement
                    if validate_video_html(video_html_tag):
                        blocks_v = llm_place_media(result, video_html_tag, media_kind="video")
                    else:
                        print("[MediaApply] Generated video HTML failed validation, skipping LLM placement")
                        blocks_v = ""
                else:
                    print(f"[MediaApply] Video generation failed: {video_html_tag}")
                    blocks_v = ""
            except Exception as e:
                print(f"[MediaApply] Exception during video-to-video generation: {str(e)}")
                blocks_v = ""
            if not blocks_v:
                # Create fallback video replacement blocks
                blocks_v = create_video_replacement_blocks_from_input_video(result, v2v_prompt, input_video_data, session_id=session_id)
            if blocks_v:
                print("[MediaApply] Applying video-to-video replacement blocks")
                before_len = len(result)
                result_after = apply_search_replace_changes(result, blocks_v)
                after_len = len(result_after)
                changed = (result_after != result)
                print(f"[MediaApply] v2v blocks length={len(blocks_v)}; html before={before_len}, after={after_len}, changed={changed}")
                if not changed:
                    print("[MediaApply] DEBUG: Replacement did not change content. Dumping first block:")
                    try:
                        first_block = blocks_v.split(REPLACE_END)[0][:1000]
                        print(first_block)
                    except Exception:
                        pass
                result = result_after
            else:
                print("[MediaApply] No v2v replacement blocks generated")
            if is_multipage and entry_html_path:
                multipage_files[entry_html_path] = result
                return format_multipage_output(multipage_files)
            return result

        # If text-to-video is enabled, insert a generated video (no input image required) and return.
        if enable_text_to_video and (result.strip().startswith('<!DOCTYPE html>') or result.strip().startswith('<html')):
            t2v_prompt = (text_to_video_prompt or user_prompt or "").strip()
            print(f"[MediaApply] Running text-to-video with prompt len={len(t2v_prompt)}")
            try:
                video_html_tag = generate_video_from_text(t2v_prompt, session_id=session_id, token=token)
                if not (video_html_tag or "").startswith("Error"):
                    # Validate video HTML before attempting placement
                    if validate_video_html(video_html_tag):
                        blocks_tv = llm_place_media(result, video_html_tag, media_kind="video")
                    else:
                        print("[MediaApply] Generated video HTML failed validation, skipping LLM placement")
                        blocks_tv = ""
                else:
                    print(f"[MediaApply] Video generation failed: {video_html_tag}")
                    blocks_tv = ""
            except Exception as e:
                print(f"[MediaApply] Exception during text-to-video generation: {str(e)}")
                blocks_tv = ""
            if not blocks_tv:
                blocks_tv = create_video_replacement_blocks_text_to_video(result, t2v_prompt, session_id=session_id)
            if blocks_tv:
                print("[MediaApply] Applying text-to-video replacement blocks")
                result = apply_search_replace_changes(result, blocks_tv)
            else:
                print("[MediaApply] No t2v replacement blocks generated")
            if is_multipage and entry_html_path:
                multipage_files[entry_html_path] = result
                return format_multipage_output(multipage_files)
            return result

        # If text-to-music is enabled, insert a generated audio player near the top of body and return.
        if enable_text_to_music and (result.strip().startswith('<!DOCTYPE html>') or result.strip().startswith('<html')):
            t2m_prompt = (text_to_music_prompt or user_prompt or "").strip()
            print(f"[MediaApply] Running text-to-music with prompt len={len(t2m_prompt)}")
            try:
                audio_html_tag = generate_music_from_text(t2m_prompt, session_id=session_id, token=token)
                if not (audio_html_tag or "").startswith("Error"):
                    blocks_tm = llm_place_media(result, audio_html_tag, media_kind="audio")
                else:
                    blocks_tm = ""
            except Exception:
                blocks_tm = ""
            if not blocks_tm:
                blocks_tm = create_music_replacement_blocks_text_to_music(result, t2m_prompt, session_id=session_id)
            if blocks_tm:
                print("[MediaApply] Applying text-to-music replacement blocks")
                result = apply_search_replace_changes(result, blocks_tm)
            else:
                print("[MediaApply] No t2m replacement blocks generated")
            if is_multipage and entry_html_path:
                multipage_files[entry_html_path] = result
                return format_multipage_output(multipage_files)
            return result

        # If an input image is provided and image-to-image is enabled, we only replace one image
        # and skip text-to-image to satisfy the requirement to replace exactly the number of uploaded images.
        if enable_image_to_image and input_image_data is not None and (result.strip().startswith('<!DOCTYPE html>') or result.strip().startswith('<html')):
            i2i_prompt = (image_to_image_prompt or user_prompt or "").strip()
            try:
                image_html_tag = generate_image_to_image(input_image_data, i2i_prompt, token=token)
                if not (image_html_tag or "").startswith("Error"):
                    blocks2 = llm_place_media(result, image_html_tag, media_kind="image")
                else:
                    blocks2 = ""
            except Exception:
                blocks2 = ""
            if not blocks2:
                blocks2 = create_image_replacement_blocks_from_input_image(result, i2i_prompt, input_image_data, max_images=1)
            if blocks2:
                result = apply_search_replace_changes(result, blocks2)
            if is_multipage and entry_html_path:
                multipage_files[entry_html_path] = result
                return format_multipage_output(multipage_files)
            return result

        if enable_text_to_image and (result.strip().startswith('<!DOCTYPE html>') or result.strip().startswith('<html')):
            t2i_prompt = (text_to_image_prompt or user_prompt or "").strip()
            print(f"[MediaApply] Running text-to-image with prompt len={len(t2i_prompt)}")
            # Single-image flow for text-to-image (LLM placement first, fallback deterministic)
            try:
                print(f"[MediaApply] Calling generate_image_with_hunyuan with prompt: {t2i_prompt[:50]}...")
                image_html_tag = generate_image_with_hunyuan(t2i_prompt, 0, token=token)
                print(f"[MediaApply] Image generation result: {image_html_tag[:200]}...")
                if not (image_html_tag or "").startswith("Error"):
                    print("[MediaApply] Attempting LLM placement of image...")
                    blocks = llm_place_media(result, image_html_tag, media_kind="image")
                    print(f"[MediaApply] LLM placement result: {len(blocks) if blocks else 0} chars")
                else:
                    print(f"[MediaApply] Image generation failed: {image_html_tag}")
                    blocks = ""
            except Exception as e:
                print(f"[MediaApply] Exception during image generation: {str(e)}")
                blocks = ""
            if not blocks:
                blocks = create_image_replacement_blocks_text_to_image_single(result, t2i_prompt)
            if blocks:
                print("[MediaApply] Applying text-to-image replacement blocks")
                result = apply_search_replace_changes(result, blocks)
    except Exception:
        import traceback
        print("[MediaApply] Exception during media application:")
        traceback.print_exc()
        return html_content
    if is_multipage and entry_html_path:
        multipage_files[entry_html_path] = result
        return format_multipage_output(multipage_files)
    return result

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

# Updated for faster Tavily search and closer prompt usage
# Uses 'advanced' search_depth and auto_parameters=True for speed and relevance

def perform_web_search(query: str, max_results: int = 5, include_domains=None, exclude_domains=None) -> str:
    """Perform web search using Tavily with default parameters"""
    if not tavily_client:
        return "Web search is not available. Please set the TAVILY_API_KEY environment variable."
    
    try:
        # Use Tavily defaults with advanced search depth for better results
        search_params = {
            "search_depth": "advanced",
            "max_results": min(max(1, max_results), 20)
        }
        if include_domains is not None:
            search_params["include_domains"] = include_domains
        if exclude_domains is not None:
            search_params["exclude_domains"] = exclude_domains

        response = tavily_client.search(query, **search_params)
        
        search_results = []
        for result in response.get('results', []):
            title = result.get('title', 'No title')
            url = result.get('url', 'No URL')
            content = result.get('content', 'No content')
            search_results.append(f"Title: {title}\nURL: {url}\nContent: {content}\n")
        
        if search_results:
            return "Web Search Results:\n\n" + "\n---\n".join(search_results)
        else:
            return "No search results found."
            
    except Exception as e:
        return f"Search error: {str(e)}"

def enhance_query_with_search(query: str, enable_search: bool) -> str:
    """Enhance the query with web search results if search is enabled"""
    if not enable_search or not tavily_client:
        return query
    
    # Perform search to get relevant information
    search_results = perform_web_search(query)
    
    # Combine original query with search results
    enhanced_query = f"""Original Query: {query}

{search_results}

Please use the search results above to help create the requested application with the most up-to-date information and best practices."""
    
    return enhanced_query

def send_to_sandbox(code):
    """Render HTML in a sandboxed iframe. Assumes full HTML is provided by prompts."""
    html_doc = (code or "").strip()
    # For preview only: inline local file URLs (e.g., file:///.../video.mp4) as data URIs so the
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
                
                # Compress video files before converting to data URI to prevent preview breaks
                if mime and mime.startswith('video/'):
                    print(f"[Sandbox] Compressing video for preview: {len(raw)} bytes")
                    raw = compress_video_for_data_uri(raw, max_size_mb=1)  # Very small limit for preview
                    print(f"[Sandbox] Compressed video size: {len(raw)} bytes")
                    
                    # If still too large, skip video embedding for preview
                    if len(raw) > 512 * 1024:  # 512KB final limit
                        print(f"[Sandbox] Video still too large after compression, using placeholder")
                        return None  # Let the replacement function handle the fallback
                
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
        
        # Add deployment message for videos that couldn't be converted
        if 'file://' in html_doc and ('video' in html_doc.lower() or '.mp4' in html_doc.lower()):
            deployment_notice = '''
            <div style="
                position: fixed; 
                top: 10px; 
                right: 10px; 
                background: #ff6b35; 
                color: white; 
                padding: 12px 16px; 
                border-radius: 8px; 
                font-family: Arial, sans-serif; 
                font-size: 14px; 
                font-weight: bold;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                z-index: 9999;
                max-width: 300px;
                text-align: center;
            ">
                🚀 Deploy app to see videos with permanent URLs!
            </div>
            '''
            # Insert the notice right after the opening body tag
            if '<body' in html_doc:
                body_end = html_doc.find('>', html_doc.find('<body')) + 1
                html_doc = html_doc[:body_end] + deployment_notice + html_doc[body_end:]
            else:
                html_doc = deployment_notice + html_doc
                
    except Exception:
        # Best-effort; continue without inlining
        pass
    encoded_html = base64.b64encode(html_doc.encode('utf-8')).decode('utf-8')
    data_uri = f"data:text/html;charset=utf-8;base64,{encoded_html}"
    iframe = f'<iframe src="{data_uri}" width="100%" height="920px" sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals allow-presentation" allow="display-capture"></iframe>'
    return iframe

def send_to_sandbox_with_refresh(code):
    """Render HTML in a sandboxed iframe with cache-busting for media generation updates."""
    import time
    html_doc = (code or "").strip()
    # For preview only: inline local file URLs (e.g., file:///.../video.mp4) as data URIs so the
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
                
                # Compress video files before converting to data URI to prevent preview breaks
                if mime and mime.startswith('video/'):
                    print(f"[Sandbox] Compressing video for preview: {len(raw)} bytes")
                    raw = compress_video_for_data_uri(raw, max_size_mb=1)  # Very small limit for preview
                    print(f"[Sandbox] Compressed video size: {len(raw)} bytes")
                    
                    # If still too large, skip video embedding for preview
                    if len(raw) > 512 * 1024:  # 512KB final limit
                        print(f"[Sandbox] Video still too large after compression, using placeholder")
                        return None  # Let the replacement function handle the fallback
                
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
        
        # Add deployment message for videos that couldn't be converted
        if 'file://' in html_doc and ('video' in html_doc.lower() or '.mp4' in html_doc.lower()):
            deployment_notice = '''
            <div style="
                position: fixed; 
                top: 10px; 
                right: 10px; 
                background: #ff6b35; 
                color: white; 
                padding: 12px 16px; 
                border-radius: 8px; 
                font-family: Arial, sans-serif; 
                font-size: 14px; 
                font-weight: bold;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                z-index: 9999;
                max-width: 300px;
                text-align: center;
            ">
                🚀 Deploy app to see videos with permanent URLs!
            </div>
            '''
            # Insert the notice right after the opening body tag
            if '<body' in html_doc:
                body_end = html_doc.find('>', html_doc.find('<body')) + 1
                html_doc = html_doc[:body_end] + deployment_notice + html_doc[body_end:]
            else:
                html_doc = deployment_notice + html_doc
                
    except Exception:
        # Best-effort; continue without inlining
        pass
    
    # Add cache-busting timestamp to force iframe refresh when content changes
    timestamp = str(int(time.time() * 1000))
    cache_bust_comment = f"<!-- refresh-{timestamp} -->"
    html_doc = cache_bust_comment + html_doc
    
    encoded_html = base64.b64encode(html_doc.encode('utf-8')).decode('utf-8')
    data_uri = f"data:text/html;charset=utf-8;base64,{encoded_html}"
    iframe = f'<iframe src="{data_uri}" width="100%" height="920px" sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals allow-presentation" allow="display-capture" key="preview-{timestamp}"></iframe>'
    return iframe

def is_streamlit_code(code: str) -> bool:
    """Heuristic check to determine if Python code is a Streamlit app."""
    if not code:
        return False
    lowered = code.lower()
    return ("import streamlit" in lowered) or ("from streamlit" in lowered) or ("st." in code and "streamlit" in lowered)

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

def demo_card_click(e: gr.EventData):
    try:
        # Get the index from the event data
        if hasattr(e, '_data') and e._data:
            # Try different ways to get the index
            if 'index' in e._data:
                index = e._data['index']
            elif 'component' in e._data and 'index' in e._data['component']:
                index = e._data['component']['index']
            elif 'target' in e._data and 'index' in e._data['target']:
                index = e._data['target']['index']
            else:
                # If we can't get the index, try to extract it from the card data
                index = 0
        else:
            index = 0
        
        # Ensure index is within bounds
        if index >= len(DEMO_LIST):
            index = 0
            
        return DEMO_LIST[index]['description']
    except (KeyError, IndexError, AttributeError) as e:
        # Return the first demo description as fallback
        return DEMO_LIST[0]['description']
def extract_text_from_image(image_path):
    """Extract text from image using OCR"""
    try:
        # Check if tesseract is available
        try:
            pytesseract.get_tesseract_version()
        except Exception:
            return "Error: Tesseract OCR is not installed. Please install Tesseract to extract text from images. See install_tesseract.md for instructions."
        
        # Read image using OpenCV
        image = cv2.imread(image_path)
        if image is None:
            return "Error: Could not read image file"
        
        # Convert to RGB (OpenCV uses BGR)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Preprocess image for better OCR results
        # Convert to grayscale
        gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
        
        # Apply thresholding to get binary image
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Extract text using pytesseract
        text = pytesseract.image_to_string(binary, config='--psm 6')
        
        return text.strip() if text.strip() else "No text found in image"
        
    except Exception as e:
        return f"Error extracting text from image: {e}"

def extract_text_from_file(file_path):
    if not file_path:
        return ""
    mime, _ = mimetypes.guess_type(file_path)
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".pdf":
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "\n".join(page.extract_text() or "" for page in reader.pages)
        elif ext in [".txt", ".md"]:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        elif ext == ".csv":
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        elif ext == ".docx":
            doc = docx.Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        elif ext.lower() in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".gif", ".webp"]:
            return extract_text_from_image(file_path)
        else:
            return ""
    except Exception as e:
        return f"Error extracting text: {e}"

def extract_website_content(url: str) -> str:
    """Extract HTML code and content from a website URL"""
    try:
        # Validate URL
        parsed_url = urlparse(url)
        if not parsed_url.scheme:
            url = "https://" + url
            parsed_url = urlparse(url)
        
        if not parsed_url.netloc:
            return "Error: Invalid URL provided"
        
        # Set comprehensive headers to mimic a real browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        
        # Create a session to maintain cookies and handle redirects
        session = requests.Session()
        session.headers.update(headers)
        
        # Make the request with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = session.get(url, timeout=15, allow_redirects=True)
                response.raise_for_status()
                break
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403 and attempt < max_retries - 1:
                    # Try with different User-Agent on 403
                    session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    continue
                else:
                    raise
        
        # Get the raw HTML content with proper encoding
        try:
            # Try to get the content with automatic encoding detection
            response.encoding = response.apparent_encoding
            raw_html = response.text
        except:
            # Fallback to UTF-8 if encoding detection fails
            raw_html = response.content.decode('utf-8', errors='ignore')
        
        # Debug: Check if we got valid HTML
        if not raw_html.strip().startswith('<!DOCTYPE') and not raw_html.strip().startswith('<html'):
            print(f"Warning: Response doesn't look like HTML. First 200 chars: {raw_html[:200]}")
            print(f"Response headers: {dict(response.headers)}")
            print(f"Response encoding: {response.encoding}")
            print(f"Apparent encoding: {response.apparent_encoding}")
            
            # Try alternative approaches
            try:
                raw_html = response.content.decode('latin-1', errors='ignore')
                print("Tried latin-1 decoding")
            except:
                try:
                    raw_html = response.content.decode('utf-8', errors='ignore')
                    print("Tried UTF-8 decoding")
                except:
                    raw_html = response.content.decode('cp1252', errors='ignore')
                    print("Tried cp1252 decoding")
        
        # Parse HTML content for analysis
        soup = BeautifulSoup(raw_html, 'html.parser')
        
        # Check if this is a JavaScript-heavy site
        script_tags = soup.find_all('script')
        if len(script_tags) > 10:
            print(f"Warning: This site has {len(script_tags)} script tags - it may be a JavaScript-heavy site")
            print("The content might be loaded dynamically and not available in the initial HTML")
        
        # Extract title
        title = soup.find('title')
        title_text = title.get_text().strip() if title else "No title found"
        
        # Extract meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc.get('content', '') if meta_desc else ""
        
        # Extract main content areas for analysis
        content_sections = []
        main_selectors = [
            'main', 'article', '.content', '.main-content', '.post-content',
            '#content', '#main', '.entry-content', '.post-body'
        ]
        
        for selector in main_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text().strip()
                if len(text) > 100:  # Only include substantial content
                    content_sections.append(text)
        
        # Extract navigation links for analysis
        nav_links = []
        nav_elements = soup.find_all(['nav', 'header'])
        for nav in nav_elements:
            links = nav.find_all('a')
            for link in links:
                link_text = link.get_text().strip()
                link_href = link.get('href', '')
                if link_text and link_href:
                    nav_links.append(f"{link_text}: {link_href}")
        
        # Extract and fix image URLs in the HTML
        img_elements = soup.find_all('img')
        for img in img_elements:
            src = img.get('src', '')
            if src:
                # Handle different URL formats
                if src.startswith('//'):
                    # Protocol-relative URL
                    absolute_src = 'https:' + src
                    img['src'] = absolute_src
                elif src.startswith('/'):
                    # Root-relative URL
                    absolute_src = urljoin(url, src)
                    img['src'] = absolute_src
                elif not src.startswith(('http://', 'https://')):
                    # Relative URL
                    absolute_src = urljoin(url, src)
                    img['src'] = absolute_src
                # If it's already absolute, keep it as is
                
                # Also check for data-src (lazy loading) and other common attributes
                data_src = img.get('data-src', '')
                if data_src and not src:
                    # Use data-src if src is empty
                    if data_src.startswith('//'):
                        absolute_data_src = 'https:' + data_src
                        img['src'] = absolute_data_src
                    elif data_src.startswith('/'):
                        absolute_data_src = urljoin(url, data_src)
                        img['src'] = absolute_data_src
                    elif not data_src.startswith(('http://', 'https://')):
                        absolute_data_src = urljoin(url, data_src)
                        img['src'] = absolute_data_src
                    else:
                        img['src'] = data_src
        
        # Also fix background image URLs in style attributes
        elements_with_style = soup.find_all(attrs={'style': True})
        for element in elements_with_style:
            style_attr = element.get('style', '')
            # Find and replace relative URLs in background-image
            import re
            bg_pattern = r'background-image:\s*url\(["\']?([^"\']+)["\']?\)'
            matches = re.findall(bg_pattern, style_attr, re.IGNORECASE)
            for match in matches:
                if match:
                    if match.startswith('//'):
                        absolute_bg = 'https:' + match
                        style_attr = style_attr.replace(match, absolute_bg)
                    elif match.startswith('/'):
                        absolute_bg = urljoin(url, match)
                        style_attr = style_attr.replace(match, absolute_bg)
                    elif not match.startswith(('http://', 'https://')):
                        absolute_bg = urljoin(url, match)
                        style_attr = style_attr.replace(match, absolute_bg)
            element['style'] = style_attr
        
        # Fix background images in <style> tags
        style_elements = soup.find_all('style')
        for style in style_elements:
            if style.string:
                style_content = style.string
                # Find and replace relative URLs in background-image
                bg_pattern = r'background-image:\s*url\(["\']?([^"\']+)["\']?\)'
                matches = re.findall(bg_pattern, style_content, re.IGNORECASE)
                for match in matches:
                    if match:
                        if match.startswith('//'):
                            absolute_bg = 'https:' + match
                            style_content = style_content.replace(match, absolute_bg)
                        elif match.startswith('/'):
                            absolute_bg = urljoin(url, match)
                            style_content = style_content.replace(match, absolute_bg)
                        elif not match.startswith(('http://', 'https://')):
                            absolute_bg = urljoin(url, match)
                            style_content = style_content.replace(match, absolute_bg)
                style.string = style_content
        
        # Extract images for analysis (after fixing URLs)
        images = []
        img_elements = soup.find_all('img')
        for img in img_elements:
            src = img.get('src', '')
            alt = img.get('alt', '')
            if src:
                images.append({'src': src, 'alt': alt})
        
        # Debug: Print some image URLs to see what we're getting
        print(f"Found {len(images)} images:")
        for i, img in enumerate(images[:5]):  # Show first 5 images
            print(f"  {i+1}. {img['alt'] or 'No alt'} - {img['src']}")
        
        # Test a few image URLs to see if they're accessible
        def test_image_url(img_url):
            try:
                test_response = requests.head(img_url, timeout=5, allow_redirects=True)
                return test_response.status_code == 200
            except:
                return False
        
        # Test first few images
        working_images = []
        for img in images[:10]:  # Test first 10 images
            if test_image_url(img['src']):
                working_images.append(img)
            else:
                print(f"  ❌ Broken image: {img['src']}")
        
        print(f"Working images: {len(working_images)} out of {len(images)}")
        
        # Get the modified HTML with absolute URLs
        modified_html = str(soup)
        
        # Clean and format the HTML for better readability
        # Remove unnecessary whitespace and comments
        import re
        cleaned_html = re.sub(r'<!--.*?-->', '', modified_html, flags=re.DOTALL)  # Remove HTML comments
        cleaned_html = re.sub(r'\s+', ' ', cleaned_html)  # Normalize whitespace
        cleaned_html = re.sub(r'>\s+<', '><', cleaned_html)  # Remove whitespace between tags
        
        # Limit HTML size to avoid token limits (keep first 15000 chars)
        if len(cleaned_html) > 15000:
            cleaned_html = cleaned_html[:15000] + "\n<!-- ... HTML truncated for length ... -->"
        
                # Check if we got any meaningful content
        if not title_text or title_text == "No title found":
            title_text = url.split('/')[-1] or url.split('/')[-2] or "Website"
        
        # If we couldn't extract any meaningful content, provide a fallback
        if len(cleaned_html.strip()) < 100:
            website_content = f"""
WEBSITE REDESIGN - EXTRACTION FAILED
====================================

URL: {url}
Title: {title_text}

ERROR: Could not extract meaningful HTML content from this website. This could be due to:
1. The website uses heavy JavaScript to load content dynamically
2. The website has anti-bot protection
3. The website requires authentication
4. The website is using advanced compression or encoding

FALLBACK APPROACH:
Please create a modern, responsive website design for a {title_text.lower()} website. Since I couldn't extract the original content, you can:

1. Create a typical layout for this type of website
2. Use placeholder content that would be appropriate
3. Include modern design elements and responsive features
4. Use a clean, professional design with good typography
5. Make it mobile-friendly and accessible

The website appears to be: {title_text}
"""
            return website_content.strip()
        
        # Compile the extracted content with the actual HTML code
        website_content = f"""
WEBSITE REDESIGN - ORIGINAL HTML CODE
=====================================

URL: {url}
Title: {title_text}
Description: {description}

PAGE ANALYSIS:
- This appears to be a {title_text.lower()} website
- Contains {len(content_sections)} main content sections
- Has {len(nav_links)} navigation links
- Includes {len(images)} images

IMAGES FOUND (use these exact URLs in your redesign):
{chr(10).join([f"• {img['alt'] or 'Image'} - {img['src']}" for img in working_images[:20]]) if working_images else "No working images found"}

ALL IMAGES (including potentially broken ones):
{chr(10).join([f"• {img['alt'] or 'Image'} - {img['src']}" for img in images[:20]]) if images else "No images found"}

ORIGINAL HTML CODE (use this as the base for redesign):
```html
{cleaned_html}
```

REDESIGN INSTRUCTIONS:
Please redesign this website with a modern, responsive layout while:
1. Preserving all the original content and structure
2. Maintaining the same navigation and functionality
3. Using the original images and their URLs (listed above)
4. Creating a modern, clean design with improved typography and spacing
5. Making it fully responsive for mobile devices
6. Using modern CSS frameworks and best practices
7. Keeping the same semantic structure but with enhanced styling

IMPORTANT: All image URLs in the HTML code above have been converted to absolute URLs and are ready to use. Make sure to preserve these exact image URLs in your redesigned version.

The HTML code above contains the complete original website structure with all images properly linked. Use it as your starting point and create a modernized version.
"""
        
        return website_content.strip()
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            return f"Error: Website blocked access (403 Forbidden). This website may have anti-bot protection. Try a different website or provide a description of what you want to build instead."
        elif e.response.status_code == 404:
            return f"Error: Website not found (404). Please check the URL and try again."
        elif e.response.status_code >= 500:
            return f"Error: Website server error ({e.response.status_code}). Please try again later."
        else:
            return f"Error accessing website: HTTP {e.response.status_code} - {str(e)}"
    except requests.exceptions.Timeout:
        return "Error: Request timed out. The website may be slow or unavailable."
    except requests.exceptions.ConnectionError:
        return "Error: Could not connect to the website. Please check your internet connection and the URL."
    except requests.exceptions.RequestException as e:
        return f"Error accessing website: {str(e)}"
    except Exception as e:
        return f"Error extracting website content: {str(e)}"


stop_generation = False


def generation_code(query: Optional[str], vlm_image: Optional[gr.Image], gen_image: Optional[gr.Image], file: Optional[str], website_url: Optional[str], _setting: Dict[str, str], _history: Optional[History], _current_model: Dict, enable_search: bool = False, language: str = "html", provider: str = "auto", enable_image_generation: bool = False, enable_image_to_image: bool = False, image_to_image_prompt: Optional[str] = None, text_to_image_prompt: Optional[str] = None, enable_image_to_video: bool = False, image_to_video_prompt: Optional[str] = None, enable_text_to_video: bool = False, text_to_video_prompt: Optional[str] = None, enable_video_to_video: bool = False, video_to_video_prompt: Optional[str] = None, input_video_data = None, enable_text_to_music: bool = False, text_to_music_prompt: Optional[str] = None, enable_image_video_to_animation: bool = False, animation_mode: str = "wan2.2-animate-move", animation_quality: str = "wan-pro", animation_video_data = None):
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
            '=== src/App.svelte ===' in last_assistant_msg):
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
                
                # Generate preview based on language
                preview_val = None
                if language == "html":
                    # Use full content for multipage detection, then extract for single-page rendering
                    _mpf2 = parse_multipage_html_output(modified_content)
                    _mpf2 = validate_and_autofix_files(_mpf2)
                    if _mpf2 and _mpf2.get('index.html'):
                        preview_val = send_to_sandbox_with_refresh(inline_multipage_into_single_preview(_mpf2))
                    else:
                        safe_preview = extract_html_document(modified_content)
                        preview_val = send_to_sandbox_with_refresh(safe_preview)
                elif language == "python" and is_streamlit_code(modified_content):
                    preview_val = send_streamlit_to_stlite(modified_content)
                
                yield {
                    code_output: modified_content,
                    history: _history,
                    sandbox: preview_val or "<div style='padding:1em;color:#888;text-align:center;'>Preview updated with your changes.</div>",
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

    # On each generate, reap old global files and cleanup previous session files
    try:
        cleanup_session_videos(session_id)
        cleanup_session_audio(session_id)
        cleanup_session_media(session_id)
        reap_old_videos()
        reap_old_audio()
        reap_old_media()
    except Exception:
        pass

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
        elif language == "svelte":
            system_prompt = FollowUpSystemPrompt  # Use generic follow-up for Svelte
        else:
            system_prompt = FollowUpSystemPrompt
    else:
        # Use language-specific prompt
        if language == "html":
            # Dynamic file selection always enabled
            system_prompt = DYNAMIC_MULTIPAGE_HTML_SYSTEM_PROMPT_WITH_SEARCH if enable_search else DYNAMIC_MULTIPAGE_HTML_SYSTEM_PROMPT
        elif language == "transformers.js":
            system_prompt = TRANSFORMERS_JS_SYSTEM_PROMPT_WITH_SEARCH if enable_search else TRANSFORMERS_JS_SYSTEM_PROMPT
        elif language == "svelte":
            system_prompt = SVELTE_SYSTEM_PROMPT_WITH_SEARCH if enable_search else SVELTE_SYSTEM_PROMPT
        elif language == "gradio":
            system_prompt = GRADIO_SYSTEM_PROMPT_WITH_SEARCH if enable_search else GRADIO_SYSTEM_PROMPT
        else:
            system_prompt = GENERIC_SYSTEM_PROMPT_WITH_SEARCH.format(language=language) if enable_search else GENERIC_SYSTEM_PROMPT.format(language=language)

    messages = history_to_messages(_history, system_prompt)

    # Extract file text and append to query if file is present
    file_text = ""
    if file:
        file_text = extract_text_from_file(file)
        if file_text:
            file_text = file_text[:5000]  # Limit to 5000 chars for prompt size
            query = f"{query}\n\n[Reference file content below]\n{file_text}"

    # Extract website content and append to query if website URL is present
    website_text = ""
    if website_url and website_url.strip():
        website_text = extract_website_content(website_url.strip())
        if website_text and not website_text.startswith("Error"):
            website_text = website_text[:8000]  # Limit to 8000 chars for prompt size
            query = f"{query}\n\n[Website content to redesign below]\n{website_text}"
        elif website_text.startswith("Error"):
            # Provide helpful guidance when website extraction fails
            fallback_guidance = """
Since I couldn't extract the website content, please provide additional details about what you'd like to build:

1. What type of website is this? (e.g., e-commerce, blog, portfolio, dashboard)
2. What are the main features you want?
3. What's the target audience?
4. Any specific design preferences? (colors, style, layout)

This will help me create a better design for you."""
            query = f"{query}\n\n[Error extracting website: {website_text}]{fallback_guidance}"

    # Enhance query with search if enabled
    enhanced_query = enhance_query_with_search(query, enable_search)

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
                    # Live streaming preview
                    preview_val = None
                    if language == "html":
                        _mp = parse_multipage_html_output(clean_code)
                        _mp = validate_and_autofix_files(_mp)
                        preview_val = send_to_sandbox(inline_multipage_into_single_preview(_mp)) if _mp.get('index.html') else send_to_sandbox(clean_code)
                    elif language == "python" and is_streamlit_code(clean_code):
                        preview_val = send_streamlit_to_stlite(clean_code)
                    yield {
                        code_output: gr.update(value=clean_code, language=get_gradio_language(language)),
                        history_output: history_to_chatbot_messages(_history),
                        sandbox: preview_val or "<div style='padding:1em;color:#888;text-align:center;'>Preview is only available for HTML or Streamlit-in-Python.</div>",
                    }
            
        except Exception as e:
            content = f"Error with GLM-4.5: {str(e)}\n\nPlease make sure HF_TOKEN environment variable is set."
        
        clean_code = remove_code_block(content)
        
        # Apply media generation (images/video/music)
        print("[Generate] Applying post-generation media to GLM-4.5 HTML output")
        final_content = apply_generated_media_to_html(
            clean_code,
            query,
            enable_text_to_image=enable_image_generation,
            enable_image_to_image=enable_image_to_image,
            input_image_data=gen_image,
            image_to_image_prompt=image_to_image_prompt,
            enable_image_to_video=enable_image_to_video,
            image_to_video_prompt=image_to_video_prompt,
            session_id=session_id,
            enable_text_to_video=enable_text_to_video,
            text_to_video_prompt=text_to_video_prompt,
            enable_video_to_video=enable_video_to_video,
            video_to_video_prompt=video_to_video_prompt,
            input_video_data=input_video_data,
            enable_text_to_music=enable_text_to_music,
            text_to_music_prompt=text_to_music_prompt,
            enable_image_video_to_animation=enable_image_video_to_animation,
            animation_mode=animation_mode,
            animation_quality=animation_quality,
            animation_video_data=animation_video_data,
            token=None,
        )
        
        _history.append([query, final_content])
        
        if language == "transformers.js":
            files = parse_transformers_js_output(clean_code)
            if files['index.html'] and files['index.js'] and files['style.css']:
                # Apply image generation if enabled
                if enable_image_generation:
                    # Create search/replace blocks for image replacement based on images found in code
                    image_replacement_blocks = create_image_replacement_blocks(files['index.html'], query)
                    if image_replacement_blocks:
                        # Apply the image replacements using existing search/replace logic
                        files['index.html'] = apply_search_replace_changes(files['index.html'], image_replacement_blocks)
                
                formatted_output = format_transformers_js_output(files)
                yield {
                    code_output: formatted_output,
                    history: _history,
                    sandbox: send_transformers_to_sandbox(files),
                    history_output: history_to_chatbot_messages(_history),
                }
            else:
                yield {
                    code_output: clean_code,
                    history: _history,
                    sandbox: "<div style='padding:1em;color:#888;text-align:center;'>Error parsing transformers.js output. Please try again.</div>",
                    history_output: history_to_chatbot_messages(_history),
                }
        elif language == "svelte":
            files = parse_svelte_output(clean_code)
            if isinstance(files, dict) and files.get('src/App.svelte'):
                # Note: Media generation (text-to-image, image-to-image, etc.) is not supported for Svelte apps
                # Only static HTML apps support automatic image/video/audio generation
                
                formatted_output = format_svelte_output(files)
                yield {
                    code_output: formatted_output,
                    history: _history,
                    sandbox: "<div style='padding:1em;color:#888;text-align:center;'>Preview is only available for HTML. Please download your Svelte code using the download button above.</div>",
                    history_output: history_to_chatbot_messages(_history),
                }
            else:
                yield {
                    code_output: clean_code,
                    history: _history,
                    sandbox: "<div style='padding:1em;color:#888;text-align:center;'>Preview is only available for HTML. Please download your Svelte code using the download button above.</div>",
                    history_output: history_to_chatbot_messages(_history),
                }
        else:
            if has_existing_content and not (clean_code.strip().startswith("<!DOCTYPE html>") or clean_code.strip().startswith("<html")):
                last_content = _history[-1][1] if _history and len(_history[-1]) > 1 else ""
                modified_content = apply_search_replace_changes(last_content, clean_code)
                clean_content = remove_code_block(modified_content)
                
                # Apply media generation (images/video/music)
                print("[Generate] Applying post-generation media to modified HTML content")
                clean_content = apply_generated_media_to_html(
                    clean_content,
                    query,
                    enable_text_to_image=enable_image_generation,
                    enable_image_to_image=enable_image_to_image,
                    input_image_data=gen_image,
                    image_to_image_prompt=image_to_image_prompt,
                    enable_image_to_video=enable_image_to_video,
                    image_to_video_prompt=image_to_video_prompt,
                    session_id=session_id,
                    enable_text_to_video=enable_text_to_video,
                    text_to_video_prompt=text_to_video_prompt,
                    enable_video_to_video=enable_video_to_video,
                    video_to_video_prompt=video_to_video_prompt,
                    input_video_data=input_video_data,
                    enable_text_to_music=enable_text_to_music,
                    text_to_music_prompt=text_to_music_prompt,
                    enable_image_video_to_animation=enable_image_video_to_animation,
                    animation_mode=animation_mode,
                    animation_quality=animation_quality,
                    animation_video_data=animation_video_data,
                    token=None,
                )
                
                yield {
                    code_output: clean_content,
                    history: _history,
                    sandbox: send_to_sandbox(clean_content) if language == "html" else "<div style='padding:1em;color:#888;text-align:center;'>Preview is only available for HTML. Please download your code using the download button above.</div>",
                    history_output: history_to_chatbot_messages(_history),
                }
            else:
                # Apply media generation (images/video/music)
                # Only apply media generation to static HTML apps, not Svelte/React/other frameworks
                if language == "html":
                    print("[Generate] Applying post-generation media to static HTML content")
                    final_content = apply_generated_media_to_html(
                        clean_code,
                        query,
                        enable_text_to_image=enable_image_generation,
                        enable_image_to_image=enable_image_to_image,
                        input_image_data=gen_image,
                        image_to_image_prompt=image_to_image_prompt,
                        text_to_image_prompt=text_to_image_prompt,
                        enable_image_to_video=enable_image_to_video,
                        image_to_video_prompt=image_to_video_prompt,
                        session_id=session_id,
                        enable_text_to_video=enable_text_to_video,
                        text_to_video_prompt=text_to_video_prompt,
                        enable_video_to_video=enable_video_to_video,
                        video_to_video_prompt=video_to_video_prompt,
                        input_video_data=input_video_data,
                        enable_text_to_music=enable_text_to_music,
                        text_to_music_prompt=text_to_music_prompt,
                        enable_image_video_to_animation=enable_image_video_to_animation,
                        animation_mode=animation_mode,
                        animation_quality=animation_quality,
                        animation_video_data=animation_video_data,
                        token=None,
                    )
                else:
                    print(f"[Generate] Skipping media generation for {language} apps (only supported for static HTML)")
                    final_content = clean_code
                
                preview_val = None
                if language == "html":
                    # Use full content for multipage detection, then extract for single-page rendering
                    _mpf2 = parse_multipage_html_output(final_content)
                    _mpf2 = validate_and_autofix_files(_mpf2)
                    if _mpf2 and _mpf2.get('index.html'):
                        preview_val = send_to_sandbox_with_refresh(inline_multipage_into_single_preview(_mpf2))
                    else:
                        safe_preview = extract_html_document(final_content)
                        preview_val = send_to_sandbox_with_refresh(safe_preview)
                elif language == "python" and is_streamlit_code(final_content):
                    preview_val = send_streamlit_to_stlite(final_content)
                yield {
                    code_output: final_content,
                    history: _history,
                    sandbox: preview_val or "<div style='padding:1em;color:#888;text-align:center;'>Preview is only available for HTML or Streamlit-in-Python.</div>",
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
                        sandbox: preview_val or "<div style='padding:1em;color:#888;text-align:center;'>Preview is only available for HTML or Streamlit-in-Python.</div>",
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
            sandbox: preview_val or "<div style='padding:1em;color:#888;text-align:center;'>Preview is only available for HTML or Streamlit-in-Python.</div>",
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
        if _current_model["id"] in ("codestral-2508", "mistral-medium-2508", "magistral-medium-2509"):
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
            if _current_model["id"] in ("codestral-2508", "mistral-medium-2508", "magistral-medium-2509"):
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
                            sandbox: "<div style='padding:1em;color:#888;text-align:center;'>" + status_line + "</div>",
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
                search_status = " (with web search)" if enable_search and tavily_client else ""
                
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
                            sandbox: preview_val or "<div style='padding:1em;color:#888;text-align:center;'>Generating transformers.js app...</div>",
                        }
                    elif has_existing_content:
                        # Model is returning search/replace changes for transformers.js - apply them
                        last_content = _history[-1][1] if _history and len(_history[-1]) > 1 else ""
                        modified_content = apply_transformers_js_search_replace_changes(last_content, content)
                        _mf = parse_transformers_js_output(modified_content)
                        yield {
                            code_output: gr.update(value=modified_content, language="html"),
                            history_output: history_to_chatbot_messages(_history),
                            sandbox: send_transformers_to_sandbox(_mf) if _mf['index.html'] else "<div style='padding:1em;color:#888;text-align:center;'>Preview is only available for HTML. Please download your code using the download button above.</div>",
                        }
                    else:
                        # Still streaming, show partial content
                        yield {
                            code_output: gr.update(value=content, language="html"),
                            history_output: history_to_chatbot_messages(_history),
                            sandbox: "<div style='padding:1em;color:#888;text-align:center;'>Generating transformers.js app...</div>",
                        }
                elif language == "svelte":
                    # For Svelte, just show the content as it streams
                    # We'll parse it properly in the final response
                    yield {
                        code_output: gr.update(value=content, language="html"),
                        history_output: history_to_chatbot_messages(_history),
                        sandbox: "<div style='padding:1em;color:#888;text-align:center;'>Generating Svelte app...</div>",
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
                                sandbox: preview_val or "<div style='padding:1em;color:#888;text-align:center;'>Preview is only available for HTML or Streamlit-in-Python.</div>",
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
                                sandbox: preview_val or "<div style='padding:1em;color:#888;text-align:center;'>Preview is only available for HTML or Streamlit-in-Python.</div>",
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
                            sandbox: preview_val or "<div style='padding:1em;color:#888;text-align:center;'>Preview is only available for HTML or Streamlit-in-Python.</div>",
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
                    sandbox: send_transformers_to_sandbox(files),
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
                    sandbox: send_transformers_to_sandbox(_mf),
                    history_output: history_to_chatbot_messages(_history),
                }
            else:
                # Fallback if parsing failed
                _history.append([query, content])
                yield {
                    code_output: content,
                    history: _history,
                    sandbox: "<div style='padding:1em;color:#888;text-align:center;'>Error parsing transformers.js output. Please try again.</div>",
                    history_output: history_to_chatbot_messages(_history),
                }
        elif language == "svelte":
            # Handle Svelte output
            files = parse_svelte_output(content)
            if isinstance(files, dict) and files.get('src/App.svelte'):
                # Model returned complete Svelte output
                formatted_output = format_svelte_output(files)
                _history.append([query, formatted_output])
                yield {
                    code_output: formatted_output,
                    history: _history,
                    sandbox: "<div style='padding:1em;color:#888;text-align:center;'>Preview is only available for HTML. Please download your Svelte code using the download button above.</div>",
                    history_output: history_to_chatbot_messages(_history),
                }
            elif has_existing_content:
                # Model returned search/replace changes for Svelte - apply them
                last_content = _history[-1][1] if _history and len(_history[-1]) > 1 else ""
                modified_content = apply_search_replace_changes(last_content, content)
                _history.append([query, modified_content])
                yield {
                    code_output: modified_content,
                    history: _history,
                    sandbox: "<div style='padding:1em;color:#888;text-align:center;'>Preview is only available for HTML. Please download your Svelte code using the download button above.</div>",
                    history_output: history_to_chatbot_messages(_history),
                }
            else:
                # Fallback if parsing failed - just use the raw content
                _history.append([query, content])
                yield {
                    code_output: content,
                    history: _history,
                    sandbox: "<div style='padding:1em;color:#888;text-align:center;'>Preview is only available for HTML. Please download your Svelte code using the download button above.</div>",
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
            
            # Apply media generation (images/video/music)
            print("[Generate] Applying post-generation media to follow-up HTML content")
            clean_content = apply_generated_media_to_html(
                clean_content,
                query,
                enable_text_to_image=enable_image_generation,
                enable_image_to_image=enable_image_to_image,
                input_image_data=gen_image,
                image_to_image_prompt=image_to_image_prompt,
                enable_image_to_video=enable_image_to_video,
                image_to_video_prompt=image_to_video_prompt,
                session_id=session_id,
                text_to_image_prompt=text_to_image_prompt,
                enable_text_to_video=enable_text_to_video,
                text_to_video_prompt=text_to_video_prompt,
                enable_video_to_video=enable_video_to_video,
                video_to_video_prompt=video_to_video_prompt,
                input_video_data=input_video_data,
                enable_text_to_music=enable_text_to_music,
                text_to_music_prompt=text_to_music_prompt,
                enable_image_video_to_animation=enable_image_video_to_animation,
                animation_mode=animation_mode,
                animation_quality=animation_quality,
                animation_video_data=animation_video_data,
                token=None,
            )
            
            # Update history with the cleaned content
            _history.append([query, clean_content])
            yield {
                code_output: clean_content,
                history: _history,
                sandbox: ((send_to_sandbox_with_refresh(inline_multipage_into_single_preview(parse_multipage_html_output(clean_content))) if parse_multipage_html_output(clean_content).get('index.html') else send_to_sandbox_with_refresh(clean_content)) if language == "html" else (send_streamlit_to_stlite(clean_content) if (language == "python" and is_streamlit_code(clean_content)) else "<div style='padding:1em;color:#888;text-align:center;'>Preview is only available for HTML or Streamlit-in-Python.</div>")),
                history_output: history_to_chatbot_messages(_history),
            }
        else:
            # Regular generation - use the content as is
            final_content = remove_code_block(content)
            
            # Apply media generation (images/video/music)
            print("[Generate] Applying post-generation media to final HTML content")
            final_content = apply_generated_media_to_html(
                final_content,
                query,
                enable_text_to_image=enable_image_generation,
                enable_image_to_image=enable_image_to_image,
                input_image_data=gen_image,
                image_to_image_prompt=image_to_image_prompt,
                text_to_image_prompt=text_to_image_prompt,
                enable_image_to_video=enable_image_to_video,
                image_to_video_prompt=image_to_video_prompt,
                session_id=session_id,
                enable_text_to_video=enable_text_to_video,
                text_to_video_prompt=text_to_video_prompt,
                enable_video_to_video=enable_video_to_video,
                video_to_video_prompt=video_to_video_prompt,
                input_video_data=input_video_data,
                enable_text_to_music=enable_text_to_music,
                text_to_music_prompt=text_to_music_prompt,
                enable_image_video_to_animation=enable_image_video_to_animation,
                animation_mode=animation_mode,
                animation_quality=animation_quality,
                animation_video_data=animation_video_data,
                token=None,
            )
            
            _history.append([query, final_content])
            preview_val = None
            if language == "html":
                # Use full content for multipage detection, then extract for single-page rendering
                _mpf = parse_multipage_html_output(final_content)
                _mpf = validate_and_autofix_files(_mpf)
                if _mpf and _mpf.get('index.html'):
                    preview_val = send_to_sandbox_with_refresh(inline_multipage_into_single_preview(_mpf))
                else:
                    safe_preview = extract_html_document(final_content)
                    preview_val = send_to_sandbox_with_refresh(safe_preview)
            elif language == "python" and is_streamlit_code(final_content):
                preview_val = send_streamlit_to_stlite(final_content)
            elif language == "gradio" or (language == "python" and is_gradio_code(final_content)):
                preview_val = send_gradio_to_lite(final_content)
            yield {
                code_output: final_content,
                history: _history,
                sandbox: preview_val or "<div style='padding:1em;color:#888;text-align:center;'>Preview is only available for HTML or Streamlit-in-Python.</div>",
                history_output: history_to_chatbot_messages(_history),
            }
    except Exception as e:
        error_message = f"Error: {str(e)}"
        yield {
            code_output: error_message,
            history_output: history_to_chatbot_messages(_history),
        }

# Deploy to Spaces logic

def add_anycoder_tag_to_readme(api, repo_id):
    """Download existing README, add anycoder tag, and upload back."""
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
                
                # Reconstruct the README
                new_content = f"---\n{frontmatter}\n---{body}"
            else:
                # Malformed frontmatter, just add tags at the end of frontmatter
                new_content = content.replace('---', '---\ntags:\n- anycoder\n---', 1)
        else:
            # No frontmatter, add it at the beginning
            new_content = f"---\ntags:\n- anycoder\n---\n\n{content}"
        
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
        client = get_inference_client("Qwen/Qwen3-Coder-480B-A35B-Instruct", "auto")
        
        imports_text = '\n'.join(import_statements)
        
        prompt = f"""Based on the following Python import statements, generate a comprehensive requirements.txt file with all necessary and commonly used related packages:

{imports_text}

Instructions:
- Include the direct packages needed for the imports
- Include commonly used companion packages and dependencies for better functionality
- Use correct PyPI package names (e.g., cv2 -> opencv-python, PIL -> Pillow, sklearn -> scikit-learn)
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

Generate a comprehensive requirements.txt that ensures the application will work smoothly:"""

        messages = [
            {"role": "system", "content": "You are a Python packaging expert specializing in creating comprehensive, production-ready requirements.txt files. Your goal is to ensure applications work smoothly by including not just direct dependencies but also commonly needed companion packages, popular extensions, and supporting libraries that developers typically need together."},
            {"role": "user", "content": prompt}
        ]
        
        response = client.chat.completions.create(
            model="Qwen/Qwen3-Coder-480B-A35B-Instruct",
            messages=messages,
            max_tokens=1024,
            temperature=0.1
        )
        
        requirements_content = response.choices[0].message.content.strip()
        
        # Clean up the response in case it includes extra formatting
        if '```' in requirements_content:
            # Extract content between code blocks
            lines = requirements_content.split('\n')
            in_code_block = False
            clean_lines = []
            for line in lines:
                if line.strip().startswith('```'):
                    in_code_block = not in_code_block
                    continue
                if in_code_block:
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
            'cv2': 'opencv-python',
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

def deploy_to_spaces_static(code):
    if not code or not code.strip():
        return  # Do nothing if code is empty
    # Use the HTML code directly for static Spaces
    app_html = wrap_html_in_static_app(code.strip())
    base_url = "https://huggingface.co/new-space"
    params = urllib.parse.urlencode({
        "name": "new-space",
        "sdk": "static"
    })
    files_params = urllib.parse.urlencode({
        "files[0][path]": "index.html",
        "files[0][content]": app_html
    })
    full_url = f"{base_url}?{params}&{files_params}"
    webbrowser.open_new_tab(full_url)

def check_hf_space_url(url: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Check if URL is a valid Hugging Face Spaces URL and extract username/project"""
    import re
    
    # Pattern to match HF Spaces URLs
    url_pattern = re.compile(
        r'^(https?://)?(huggingface\.co|hf\.co)/spaces/([\w-]+)/([\w-]+)$',
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
        
        # Try to fetch the main file based on SDK
        sdk = space_info.sdk
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
        
        # If still no main file found, try to list repository files and find Python files
        if not main_file and sdk in ["streamlit", "gradio"]:
            try:
                from huggingface_hub import list_repo_files
                files = list_repo_files(repo_id=f"{username}/{project_name}", repo_type="space")
                
                # Look for Python files that might be the main file (root and src/ directory)
                python_files = [f for f in files if f.endswith('.py') and not f.startswith('.') and 
                              (('/' not in f) or f.startswith('src/'))]
                
                for py_file in python_files:
                    try:
                        content = api.hf_hub_download(
                            repo_id=f"{username}/{project_name}",
                            filename=py_file,
                            repo_type="space"
                        )
                        main_file = py_file
                        break
                    except:
                        continue
            except:
                pass
        
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
                files = list_repo_files(repo_id=f"{username}/{project_name}", repo_type="space")
                available_files = [f for f in files if not f.startswith('.') and not f.endswith('.md')]
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

def _fetch_hf_model_readme(repo_id: str) -> Optional[str]:
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

def _fetch_github_readme(owner: str, repo: str) -> Optional[str]:
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

def _extract_transformers_or_diffusers_snippet(markdown_text: str) -> Tuple[Optional[str], Optional[str]]:
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

def _infer_task_from_context(snippet: Optional[str], pipeline_tag: Optional[str]) -> str:
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

def _generate_streamlit_wrapper(gradio_code: str) -> str:
    """Convert a simple Gradio app into a Streamlit wrapper by embedding via components if needed.
    If code is already Streamlit, return as is. Otherwise, provide a basic Streamlit UI calling the same pipeline.
    """
    # For now, simply return a minimal placeholder to keep scope tight; prefer Gradio by default.
    return (
        "import streamlit as st\n"
        "st.markdown('This model is best used with a Gradio app in this tool. Switch framework to Gradio for a runnable demo.')\n"
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
        /* Darker chat bubbles for better contrast in dark theme */
        #beta_chat .message.user, #beta_chat .message.assistant {
            background: rgba(60, 60, 60, 0.85);
            color: #f5f5f5;
        }
        #beta_chat .message.user {
            background: rgba(70, 70, 70, 0.95);
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
        beta_toggle = gr.Checkbox(
            value=False,
            label="Beta: Chat UI",
            info="Switch to the new chat-based sidebar interface"
        )

        # Simple chat-based controller for sidebar
        sidebar_chatbot = gr.Chatbot(
            type="messages",
            show_label=False,
            height=320,
            layout="bubble",
            bubble_full_width=True,
            group_consecutive_messages=True,
            visible=False,
            elem_id="beta_chat"
        )
        sidebar_msg = gr.MultimodalTextbox(
            placeholder=(
                "Describe what to build. Examples: 'use streamlit', 'text to video: <prompt>'. "
                "See Advanced Commands below for the full list."
            ),
            submit_btn=True,
            stop_btn=False,
            show_label=False,
            sources=["upload", "microphone"],
            visible=False
        )
        chat_clear_btn = gr.ClearButton([sidebar_msg, sidebar_chatbot], visible=False)

        # Collapsed Advanced Commands reference
        with gr.Accordion(label="Advanced Commands", open=False, visible=False) as advanced_commands:
            gr.Markdown(
                value=(
                    "### Command Reference\n"
                    "- **Language**: 'use streamlit' | 'use gradio' | 'use html'\n"
                    "- **Web search**: 'enable web search' | 'disable web search'\n"
                    "- **Model**: 'model <name>' (exact match to items in the Model dropdown)\n"
                    "- **Website redesign**: include a URL in your message (e.g., 'https://example.com')\n"
                    "- **Text → Image**: 'generate images: <prompt>' or 'text to image: <prompt>'\n"
                    "- **Image → Image**: 'image to image: <prompt>' (attach an image)\n"
                    "- **Image → Video**: 'image to video: <prompt>' (attach an image)\n"
                    "- **Text → Video**: 'text to video: <prompt>' or 'generate video: <prompt>'\n"
                    "- **Files & media**: attach documents or images directly; the first image is used for generation, the first non-image is treated as a reference file\n"
                    "- **Multiple directives**: separate with commas. The first segment is the main build prompt.\n\n"
                    "Examples:\n"
                    "- anycoder coffee shop, text to video: coffee pouring into cup\n"
                    "- redesign https://example.com, use streamlit, enable web search\n"
                    "- dashboard ui, generate images: minimalist pastel hero"
                )
            )
        
        # Theme Selector (hidden for end users, developers can modify code)
        with gr.Column(visible=False):
            theme_dropdown = gr.Dropdown(
                choices=list(THEME_CONFIGS.keys()),
                value=current_theme_name,
                label="Select Theme",
                info="Choose your preferred visual style"
            )
            theme_description = gr.Markdown("")
            apply_theme_btn = gr.Button("Apply Theme", variant="primary", size="sm")
            theme_status = gr.Markdown("")
        
        # Unified Import section
        import_header_md = gr.Markdown("📥 Import Project (Space, GitHub, or Model)")
        load_project_url = gr.Textbox(
            label="Project URL",
            placeholder="https://huggingface.co/spaces/user/space OR https://huggingface.co/user/model OR https://github.com/owner/repo",
            lines=1
        , visible=True)
        load_project_btn = gr.Button("Import Project", variant="secondary", size="sm", visible=True)
        load_project_status = gr.Markdown(visible=False)
        
        input = gr.Textbox(
            label="What would you like to build?",
            placeholder="Describe your application...",
            lines=3,
            visible=True
        )
        # Language dropdown for code generation (add Streamlit and Gradio as first-class options)
        language_choices = [
            "html", "gradio", "transformers.js", "streamlit", "python", "svelte", "c", "cpp", "markdown", "latex", "json", "css", "javascript", "jinja2", "typescript", "yaml", "dockerfile", "shell", "r", "sql", "sql-msSQL", "sql-mySQL", "sql-mariaDB", "sql-sqlite", "sql-cassandra", "sql-plSQL", "sql-hive", "sql-pgSQL", "sql-gql", "sql-gpSQL", "sql-sparkSQL", "sql-esper"
        ]
        language_dropdown = gr.Dropdown(
            choices=language_choices,
            value="html",
            label="Code Language",
            visible=True
        )
        website_url_input = gr.Textbox(
            label="website for redesign",
            placeholder="https://example.com",
            lines=1,
            visible=True
        )
        file_input = gr.File(
            label="Reference file (OCR only)",
            file_types=[".pdf", ".txt", ".md", ".csv", ".docx", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".gif", ".webp"],
            visible=True
        )
        image_input = gr.Image(
            label="UI design image",
            visible=False
        )
        # New hidden image input used for VLMs, image-to-image, and image-to-video
        generation_image_input = gr.Image(
            label="image for generation",
            visible=False
        )
        image_to_image_prompt = gr.Textbox(
            label="Image-to-Image Prompt",
            placeholder="Describe how to transform the uploaded image (e.g., 'Turn the cat into a tiger.')",
            lines=2,
            visible=False
        )
        with gr.Row():
            btn = gr.Button("Generate", variant="primary", size="lg", scale=2, visible=True)
            clear_btn = gr.Button("Clear", variant="secondary", size="sm", scale=1, visible=True)
        # --- Move deploy/app name/sdk here, right before web search ---
        space_name_input = gr.Textbox(
            label="app name (e.g. my-cool-app)",
            placeholder="Enter your app name",
            lines=1,
            visible=False
        )
        sdk_choices = [
            ("Gradio (Python)", "gradio"),
            ("Streamlit (Python)", "streamlit"),
            ("Static (HTML)", "static"),
            ("Transformers.js", "transformers.js"),
            ("Svelte", "svelte")
        ]
        sdk_dropdown = gr.Dropdown(
            choices=[x[0] for x in sdk_choices],
            value="Static (HTML)",
            label="App SDK",
            visible=False
        )
        deploy_btn = gr.Button("🚀 Deploy App", variant="primary", visible=False)
        deploy_status = gr.Markdown(visible=False, label="Deploy status")
        # --- End move ---
        search_toggle = gr.Checkbox(
            label="🔍 Web search",
            value=False,
            visible=True
        )
        # Dynamic multipage is always enabled; no toggle in UI
        # Image generation toggles
        image_generation_toggle = gr.Checkbox(
            label="🎨 Generate Images (text → image)",
            value=False,
            visible=True,
            info="Include generated images in your outputs using HunyuanImage-2.1"
        )
        text_to_image_prompt = gr.Textbox(
            label="Text-to-Image Prompt",
            placeholder="Describe the image to generate (e.g., 'A minimalist dashboard hero illustration in pastel colors.')",
            lines=2,
            visible=False
        )
        image_to_image_toggle = gr.Checkbox(
            label="🖼️ Image to Image (uses input image)",
            value=False,
            visible=True,
            info="Transform your uploaded image using Nano Banana"
        )
        image_to_video_toggle = gr.Checkbox(
            label="🎞️ Image to Video (uses input image)",
            value=False,
            visible=True,
            info="Generate a short video from your uploaded image using Lightricks LTX-Video"
        )
        image_to_video_prompt = gr.Textbox(
            label="Image-to-Video Prompt",
            placeholder="Describe the motion (e.g., 'The cat starts to dance')",
            lines=2,
            visible=False
        )

        # Text-to-Video
        text_to_video_toggle = gr.Checkbox(
            label="📹 Generate Video (text → video)",
            value=False,
            visible=True,
            info="Generate a short video directly from your prompt using Wan-AI/Wan2.2-TI2V-5B"
        )
        text_to_video_prompt = gr.Textbox(
            label="Text-to-Video Prompt",
            placeholder="Describe the video to generate (e.g., 'A young man walking on the street')",
            lines=2,
            visible=False
        )

        # Video-to-Video
        video_to_video_toggle = gr.Checkbox(
            label="🎬 Video to Video (uses input video)",
            value=False,
            visible=True,
            info="Transform your uploaded video using Decart AI's Lucy Pro V2V"
        )
        video_to_video_prompt = gr.Textbox(
            label="Video-to-Video Prompt",
            placeholder="Describe the transformation (e.g., 'Change their shirt to black and shiny leather')",
            lines=2,
            visible=False
        )
        video_input = gr.Video(
            label="Input video for transformation",
            visible=False
        )

        # Text-to-Music
        text_to_music_toggle = gr.Checkbox(
            label="🎵 Generate Music (text → music)",
            value=False,
            visible=True,
            info="Compose short music from your prompt using ElevenLabs Music"
        )
        text_to_music_prompt = gr.Textbox(
            label="Text-to-Music Prompt",
            placeholder="Describe the music to generate (e.g., 'Epic orchestral theme with soaring strings and powerful brass')",
            lines=2,
            visible=False
        )

        # Image+Video to Animation
        image_video_to_animation_toggle = gr.Checkbox(
            label="🎭 Character Animation (uses input image + video)",
            value=False,
            visible=True,
            info="Animate characters using Wan2.2-Animate with reference image and template video"
        )
        animation_mode_dropdown = gr.Dropdown(
            label="Animation Mode",
            choices=[
                ("Move Mode (animate character with video motion)", "wan2.2-animate-move"),
                ("Mix Mode (replace character in video)", "wan2.2-animate-mix")
            ],
            value="wan2.2-animate-move",
            visible=False,
            info="Move: animate image character with video motion. Mix: replace video character with image character"
        )
        animation_quality_dropdown = gr.Dropdown(
            label="Animation Quality",
            choices=[
                ("Professional (25fps, 720p)", "wan-pro"),
                ("Standard (15fps, 720p)", "wan-std")
            ],
            value="wan-pro",
            visible=False,
            info="Higher quality takes more time to generate"
        )
        animation_video_input = gr.Video(
            label="Template video for animation (upload a video to use as motion template or character replacement source)",
            visible=False
        )

        # LLM-guided media placement is now always on (no toggle in UI)

        def on_image_to_image_toggle(toggled, beta_enabled):
            # Only show in classic mode (beta disabled)
            vis = bool(toggled) and not bool(beta_enabled)
            return gr.update(visible=vis), gr.update(visible=vis)

        def on_text_to_image_toggle(toggled, beta_enabled):
            vis = bool(toggled) and not bool(beta_enabled)
            return gr.update(visible=vis)

        image_to_image_toggle.change(
            on_image_to_image_toggle,
            inputs=[image_to_image_toggle, beta_toggle],
            outputs=[generation_image_input, image_to_image_prompt]
        )
        def on_image_to_video_toggle(toggled, beta_enabled):
            vis = bool(toggled) and not bool(beta_enabled)
            return gr.update(visible=vis), gr.update(visible=vis)

        image_to_video_toggle.change(
            on_image_to_video_toggle,
            inputs=[image_to_video_toggle, beta_toggle],
            outputs=[generation_image_input, image_to_video_prompt]
        )
        image_generation_toggle.change(
            on_text_to_image_toggle,
            inputs=[image_generation_toggle, beta_toggle],
            outputs=[text_to_image_prompt]
        )
        text_to_video_toggle.change(
            on_text_to_image_toggle,
            inputs=[text_to_video_toggle, beta_toggle],
            outputs=[text_to_video_prompt]
        )
        video_to_video_toggle.change(
            on_image_to_video_toggle,
            inputs=[video_to_video_toggle, beta_toggle],
            outputs=[video_input, video_to_video_prompt]
        )
        text_to_music_toggle.change(
            on_text_to_image_toggle,
            inputs=[text_to_music_toggle, beta_toggle],
            outputs=[text_to_music_prompt]
        )
        
        def on_image_video_to_animation_toggle(toggled, beta_enabled):
            vis = bool(toggled) and not bool(beta_enabled)
            return (
                gr.update(visible=vis),  # generation_image_input
                gr.update(visible=vis),  # animation_mode_dropdown
                gr.update(visible=vis),  # animation_quality_dropdown
                gr.update(visible=vis),  # animation_video_input
            )
        
        image_video_to_animation_toggle.change(
            on_image_video_to_animation_toggle,
            inputs=[image_video_to_animation_toggle, beta_toggle],
            outputs=[generation_image_input, animation_mode_dropdown, animation_quality_dropdown, animation_video_input]
        )
        model_dropdown = gr.Dropdown(
            choices=[model['name'] for model in AVAILABLE_MODELS],
            value=DEFAULT_MODEL_NAME,
            label="Model",
            visible=True
        )
        provider_state = gr.State("auto")
        quick_start_md = gr.Markdown("**Quick start**", visible=True)
        with gr.Column(visible=True) as quick_examples_col:
            for i, demo_item in enumerate(DEMO_LIST[:3]):
                demo_card = gr.Button(
                    value=demo_item['title'], 
                    variant="secondary",
                    size="sm"
                )
                demo_card.click(
                    fn=lambda idx=i: gr.update(value=DEMO_LIST[idx]['description']),
                    outputs=input
                )
        if not tavily_client:
            gr.Markdown("⚠️ Web search unavailable", visible=True)
        # Remove model display and web search available line
        def on_model_change(model_name):
            for m in AVAILABLE_MODELS:
                if m['name'] == model_name:
                    return m, update_image_input_visibility(m)
            return AVAILABLE_MODELS[0], update_image_input_visibility(AVAILABLE_MODELS[0])
        def save_prompt(input):
            return {setting: {"system": input}}
        model_dropdown.change(
            lambda model_name: on_model_change(model_name),
            inputs=model_dropdown,
            outputs=[current_model, image_input]
        )
        # --- Remove deploy/app name/sdk from bottom column ---
        # (delete the gr.Column() block containing space_name_input, sdk_dropdown, deploy_btn, deploy_status)

    with gr.Column() as main_column:
        with gr.Tabs():
            with gr.Tab("Preview"):
                sandbox = gr.HTML(label="Live preview")
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
                gr.update(),
                [],
                [],
                gr.update(value="", visible=False),
                gr.update(value="🚀 Deploy App", visible=False),
                gr.update(),  # keep import header as-is
                gr.update(),  # keep import button as-is
                gr.update()   # language dropdown - no change
            ]

        kind, meta = _parse_repo_or_model_url(url)
        if kind == "hf_space":
            status, code = load_project_from_url(url)
            # Extract space info for deployment
            is_valid, username, project_name = check_hf_space_url(url)
            space_info = f"{username}/{project_name}" if is_valid else ""
            loaded_history = [[f"Imported Space from {url}", code]]
            
            # Determine the correct language/framework based on the imported content
            code_lang = "html"  # default
            framework_type = "html"  # for language dropdown
            if is_streamlit_code(code) or is_gradio_code(code):
                code_lang = "python"
                framework_type = "python"
            elif "=== index.html ===" in code and "=== index.js ===" in code and "=== style.css ===" in code:
                # This is a transformers.js app with the combined format
                code_lang = "html"  # Use html for code display
                framework_type = "transformers.js"  # But set dropdown to transformers.js
            
            # Return the updates with proper language settings
            return [
                gr.update(value=status, visible=True),
                gr.update(value=code, language=code_lang),  # Use html for transformers.js display
                gr.update(value=""),
                gr.update(value="", visible=False),  # hide import textbox after submit
                loaded_history,
                history_to_chatbot_messages(loaded_history),
                gr.update(value=space_info, visible=True),
                gr.update(value="Update Existing Space", visible=True),
                gr.update(visible=False),  # hide import header
                gr.update(visible=False),  # hide import button
                gr.update(value=framework_type)  # set language dropdown to framework type
            ]
        else:
            # GitHub or HF model → return raw snippet for LLM starting point
            status, code, _ = import_repo_to_app(url)
            loaded_history = [[f"Imported Repo/Model from {url}", code]]
            code_lang = "python"
            framework_type = "python"
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
                gr.update(value=""),
                gr.update(value="", visible=False),  # hide import textbox after submit
                loaded_history,
                history_to_chatbot_messages(loaded_history),
                gr.update(value="", visible=False),
                gr.update(value="🚀 Deploy App", visible=False),
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

    def update_sdk_based_on_language(language):
        if language == "transformers.js":
            return gr.update(value="Transformers.js")
        elif language == "svelte":
            return gr.update(value="Svelte")
        elif language == "html":
            return gr.update(value="Static (HTML)")
        elif language == "streamlit":
            return gr.update(value="Streamlit (Python)")
        elif language == "gradio":
            return gr.update(value="Gradio (Python)")
        else:
            return gr.update(value="Gradio (Python)")

    language_dropdown.change(update_code_language, inputs=language_dropdown, outputs=code_output)
    language_dropdown.change(update_sdk_based_on_language, inputs=language_dropdown, outputs=sdk_dropdown)

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
            ]
        else:
            return [
                gr.update(visible=True),                  # code_output shown
                gr.update(visible=False),                 # tjs_group hidden
                gr.update(),
                gr.update(),
                gr.update(),
            ]

    language_dropdown.change(
        toggle_editors,
        inputs=[language_dropdown, code_output],
        outputs=[code_output, tjs_group, tjs_html_code, tjs_js_code, tjs_css_code],
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

        files = parse_multipage_html_output(code_text or "")
        files = validate_and_autofix_files(files)

        if not isinstance(files, dict) or len(files) <= 1:
            # No multi-file content; keep single editor
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
        
        # Hide single editor, show appropriate group based on file count
        updates = [gr.update(visible=False)]  # code_output
        
        if num_files == 2:
            updates.extend([
                gr.update(visible=True),     # static_group_2
                gr.update(visible=False),    # static_group_3  
                gr.update(visible=False),    # static_group_4
                gr.update(visible=False),    # static_group_5plus
            ])
            # Populate 2-file group (tab labels + code content)
            path1, path2 = ordered_paths[0], ordered_paths[1]
            updates.extend([
                gr.update(label=path1), gr.update(value=files.get(path1, ''), label=path1, language=_lang_for(path1)),
                gr.update(label=path2), gr.update(value=files.get(path2, ''), label=path2, language=_lang_for(path2)),
                # Empty updates for unused groups
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
            ])
        elif num_files == 3:
            updates.extend([
                gr.update(visible=False),    # static_group_2
                gr.update(visible=True),     # static_group_3  
                gr.update(visible=False),    # static_group_4
                gr.update(visible=False),    # static_group_5plus
            ])
            # Populate 3-file group (tab labels + code content)
            path1, path2, path3 = ordered_paths[0], ordered_paths[1], ordered_paths[2]
            updates.extend([
                # Empty updates for 2-file group
                gr.update(), gr.update(), gr.update(), gr.update(),
                # Populate 3-file group
                gr.update(label=path1), gr.update(value=files.get(path1, ''), label=path1, language=_lang_for(path1)),
                gr.update(label=path2), gr.update(value=files.get(path2, ''), label=path2, language=_lang_for(path2)),
                gr.update(label=path3), gr.update(value=files.get(path3, ''), label=path3, language=_lang_for(path3)),
                # Empty updates for unused groups
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
            ])
        elif num_files == 4:
            updates.extend([
                gr.update(visible=False),    # static_group_2
                gr.update(visible=False),    # static_group_3  
                gr.update(visible=True),     # static_group_4
                gr.update(visible=False),    # static_group_5plus
            ])
            # Populate 4-file group (tab labels + code content)
            paths = ordered_paths[:4]
            updates.extend([
                # Empty updates for 2-file and 3-file groups
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                # Populate 4-file group
                gr.update(label=paths[0]), gr.update(value=files.get(paths[0], ''), label=paths[0], language=_lang_for(paths[0])),
                gr.update(label=paths[1]), gr.update(value=files.get(paths[1], ''), label=paths[1], language=_lang_for(paths[1])),
                gr.update(label=paths[2]), gr.update(value=files.get(paths[2], ''), label=paths[2], language=_lang_for(paths[2])),
                gr.update(label=paths[3]), gr.update(value=files.get(paths[3], ''), label=paths[3], language=_lang_for(paths[3])),
                # Empty updates for 5+ group
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
            ])
        else:  # 5+ files
            updates.extend([
                gr.update(visible=False),    # static_group_2
                gr.update(visible=False),    # static_group_3  
                gr.update(visible=False),    # static_group_4
                gr.update(visible=True),     # static_group_5plus
            ])
            # Populate 5+ file group (show first 5) (tab labels + code content)
            paths = ordered_paths[:5]
            updates.extend([
                # Empty updates for 2-file, 3-file, and 4-file groups
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                # Populate 5+ file group
                gr.update(label=paths[0]), gr.update(value=files.get(paths[0], ''), label=paths[0], language=_lang_for(paths[0])),
                gr.update(label=paths[1]), gr.update(value=files.get(paths[1], ''), label=paths[1], language=_lang_for(paths[1])),
                gr.update(label=paths[2]), gr.update(value=files.get(paths[2], ''), label=paths[2], language=_lang_for(paths[2])),
                gr.update(label=paths[3]), gr.update(value=files.get(paths[3], ''), label=paths[3], language=_lang_for(paths[3])),
                gr.update(label=paths[4]), gr.update(value=files.get(paths[4], ''), label=paths[4], language=_lang_for(paths[4]))
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

    def preview_logic(code, language, html_part=None, js_part=None, css_part=None):
        if language == "html":
            # If the content is a multi-page block, inline for preview; else render directly
            files = parse_multipage_html_output(code)
            files = validate_and_autofix_files(files)
            if files and files.get('index.html'):
                merged = inline_multipage_into_single_preview(files)
                return send_to_sandbox(merged)
            return send_to_sandbox(code)
        if language == "streamlit":
            return send_streamlit_to_stlite(code) if is_streamlit_code(code) else "<div style='padding:1em;color:#888;text-align:center;'>Add `import streamlit as st` to enable Streamlit preview.</div>"
        if language == "gradio":
            return send_gradio_to_lite(code) if is_gradio_code(code) else "<div style='padding:1em;color:#888;text-align:center;'>Add `import gradio as gr` to enable Gradio preview.</div>"
        if language == "python" or is_streamlit_code(code):
            if is_streamlit_code(code):
                return send_streamlit_to_stlite(code)
            return "<div style='padding:1em;color:#888;text-align:center;'>Preview available only for Streamlit apps in Python. Add `import streamlit as st`.</div>"
        if language == "transformers.js":
            # Prefer values passed from multi-file editors if present; fallback to parsing single editor content
            files = {'index.html': html_part or '', 'index.js': js_part or '', 'style.css': css_part or ''}
            if not (files['index.html'] or files['index.js'] or files['style.css']):
                files = parse_transformers_js_output(code)
            if files['index.html']:
                return send_transformers_to_sandbox(files)
            return "<div style='padding:1em;color:#888;text-align:center;'>Preview is only available for HTML. Please download your code using the download button above.</div>"
        if language == "svelte":
            return "<div style='padding:1em;color:#888;text-align:center;'>Preview is only available for HTML. Please download your Svelte code and deploy it to see the result.</div>"
        return "<div style='padding:1em;color:#888;text-align:center;'>Preview is only available for HTML.</div>"

    # Direct preview updates from multi-file editor changes
    def preview_from_tjs_editors(html_code, js_code, css_code):
        files = {'index.html': html_code or '', 'index.js': js_code or '', 'style.css': css_code or ''}
        if files['index.html']:
            return send_transformers_to_sandbox(files)
        return gr.update()

    tjs_html_code.change(preview_from_tjs_editors, inputs=[tjs_html_code, tjs_js_code, tjs_css_code], outputs=sandbox)
    tjs_js_code.change(preview_from_tjs_editors, inputs=[tjs_html_code, tjs_js_code, tjs_css_code], outputs=sandbox)
    tjs_css_code.change(preview_from_tjs_editors, inputs=[tjs_html_code, tjs_js_code, tjs_css_code], outputs=sandbox)

    def show_deploy_components(*args):
        return [gr.Textbox(visible=True), gr.Dropdown(visible=True), gr.Button(visible=True)]

    def hide_deploy_components(*args):
        return [gr.Textbox(visible=False), gr.Dropdown(visible=False), gr.Button(visible=False)]
    
    def update_deploy_button_text(space_name):
        """Update deploy button text based on whether it's a new space or update"""
        if "/" in space_name.strip():
            return gr.update(value="🔄 Update Space")
        else:
            return gr.update(value="🚀 Deploy App")
    
    def preserve_space_info_for_followup(history):
        """Check if this is a followup on an imported project and preserve space info"""
        if not history or len(history) == 0:
            return [gr.update(), gr.update()]
        
        # Look for imported project pattern in history
        for user_msg, assistant_msg in history:
            if assistant_msg and 'IMPORTED PROJECT FROM HUGGING FACE SPACE' in assistant_msg:
                # Extract space name from the imported project info
                import re
                space_match = re.search(r'Space:\s*([^\s\n]+)', assistant_msg)
                if space_match:
                    space_name = space_match.group(1)
                    return [
                        gr.update(value=space_name, visible=True),  # Update space name
                        gr.update(value="🔄 Update Space", visible=True)  # Update button text
                    ]
        
        # No imported project found, return no changes
        return [gr.update(), gr.update()]

    # Unified import event
    load_project_btn.click(
        handle_import_project,
        inputs=[load_project_url],
        outputs=[
            load_project_status,
            code_output,
            sandbox,
            load_project_url,
            history,
            history_output,
            space_name_input,
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
        # Keep sidebar as is; hide the status
        return [gr.update(), gr.update(visible=False)]

    btn.click(
        begin_generation_ui,
        inputs=None,
        outputs=[sidebar, generating_status],
        show_progress="hidden",
    ).then(
        generation_code,
        inputs=[input, image_input, generation_image_input, file_input, website_url_input, setting, history, current_model, search_toggle, language_dropdown, provider_state, image_generation_toggle, image_to_image_toggle, image_to_image_prompt, text_to_image_prompt, image_to_video_toggle, image_to_video_prompt, text_to_video_toggle, text_to_video_prompt, video_to_video_toggle, video_to_video_prompt, video_input, text_to_music_toggle, text_to_music_prompt, image_video_to_animation_toggle, animation_mode_dropdown, animation_quality_dropdown, animation_video_input],
        outputs=[code_output, history, sandbox, history_output]
    ).then(
        end_generation_ui,
        inputs=None,
        outputs=[sidebar, generating_status]
    ).then(
        # After generation, toggle editors for transformers.js and populate
        toggle_editors,
        inputs=[language_dropdown, code_output],
        outputs=[code_output, tjs_group, tjs_html_code, tjs_js_code, tjs_css_code]
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
        show_deploy_components,
        None,
        [space_name_input, sdk_dropdown, deploy_btn]
    ).then(
        preserve_space_info_for_followup,
        inputs=[history],
        outputs=[space_name_input, deploy_btn]
    )

    # Pressing Enter in the main input should trigger generation and collapse the sidebar
    input.submit(
        begin_generation_ui,
        inputs=None,
        outputs=[sidebar, generating_status],
        show_progress="hidden",
    ).then(
        generation_code,
        inputs=[input, image_input, generation_image_input, file_input, website_url_input, setting, history, current_model, search_toggle, language_dropdown, provider_state, image_generation_toggle, image_to_image_toggle, image_to_image_prompt, text_to_image_prompt, image_to_video_toggle, image_to_video_prompt, text_to_video_toggle, text_to_video_prompt, video_to_video_toggle, video_to_video_prompt, video_input, text_to_music_toggle, text_to_music_prompt],
        outputs=[code_output, history, sandbox, history_output]
    ).then(
        end_generation_ui,
        inputs=None,
        outputs=[sidebar, generating_status]
    ).then(
        show_deploy_components,
        None,
        [space_name_input, sdk_dropdown, deploy_btn]
    ).then(
        preserve_space_info_for_followup,
        inputs=[history],
        outputs=[space_name_input, deploy_btn]
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
    def apply_chat_command(message, chat_messages):
        # Support plain text or dict from MultimodalTextbox
        text = message if isinstance(message, str) else (message.get("text", "") if isinstance(message, dict) else "")
        files = []
        if isinstance(message, dict):
            files = message.get("files", []) or []

        # Defaults to skip updates where unchanged
        upd_input = gr.skip()
        upd_language = gr.skip()
        upd_url = gr.skip()
        upd_file = gr.skip()
        upd_image_for_gen = gr.skip()
        upd_search = gr.skip()
        upd_img_gen = gr.skip()
        upd_t2i_prompt = gr.skip()
        upd_i2i_toggle = gr.skip()
        upd_i2i_prompt = gr.skip()
        upd_i2v_toggle = gr.skip()
        upd_i2v_prompt = gr.skip()
        upd_t2v_toggle = gr.skip()
        upd_t2v_prompt = gr.skip()
        upd_v2v_toggle = gr.skip()
        upd_v2v_prompt = gr.skip()
        upd_video_input = gr.skip()
        upd_model_dropdown = gr.skip()
        upd_current_model = gr.skip()
        upd_t2m_toggle = gr.skip()
        upd_t2m_prompt = gr.skip()
        upd_iv2a_toggle = gr.skip()
        upd_anim_mode = gr.skip()
        upd_anim_quality = gr.skip()
        upd_anim_video = gr.skip()

        # Split by comma to separate main prompt and directives
        segments = [seg.strip() for seg in (text or "").split(",") if seg.strip()]
        main_prompt = segments[0] if segments else text

        # Helper to get text after ':' in original casing
        def after_colon(original_segment: str) -> str:
            parts = original_segment.split(":", 1)
            return parts[1].strip() if len(parts) == 2 else ""

        # Process directives from all segments (including first if user puts directives there),
        # but always set the main build prompt from the first segment only
        for seg in segments:
            seg_norm = seg.lower()
            # Language
            if "use streamlit" in seg_norm:
                upd_language = gr.update(value="streamlit")
            elif "use gradio" in seg_norm:
                upd_language = gr.update(value="gradio")
            elif "use html" in seg_norm or "as html" in seg_norm:
                upd_language = gr.update(value="html")

            # Web search
            if (
                "enable web search" in seg_norm
                or "web search on" in seg_norm
                or "with web search" in seg_norm
                or "search the web" in seg_norm
            ):
                upd_search = gr.update(value=True)
            if (
                "disable web search" in seg_norm
                or "no web search" in seg_norm
                or "web search off" in seg_norm
            ):
                upd_search = gr.update(value=False)

            # Text-to-image
            if ("generate images" in seg_norm) or ("text to image" in seg_norm) or ("text-to-image" in seg_norm):
                upd_img_gen = gr.update(value=True)
                p = after_colon(seg)
                if p:
                    upd_t2i_prompt = gr.update(value=p)

            # Image-to-image
            if ("image to image" in seg_norm) or ("image-to-image" in seg_norm) or ("transform image" in seg_norm):
                upd_i2i_toggle = gr.update(value=True)
                p = after_colon(seg)
                if p:
                    upd_i2i_prompt = gr.update(value=p)

            # Image-to-video
            if ("image to video" in seg_norm) or ("image-to-video" in seg_norm):
                upd_i2v_toggle = gr.update(value=True)
                p = after_colon(seg)
                if p:
                    upd_i2v_prompt = gr.update(value=p)

            # Text-to-video
            if ("text to video" in seg_norm) or ("text-to-video" in seg_norm) or ("generate video" in seg_norm):
                upd_t2v_toggle = gr.update(value=True)
                p = after_colon(seg)
                if p:
                    upd_t2v_prompt = gr.update(value=p)

            # Video-to-video
            if ("video to video" in seg_norm) or ("video-to-video" in seg_norm) or ("transform video" in seg_norm):
                upd_v2v_toggle = gr.update(value=True)
                p = after_colon(seg)
                if p:
                    upd_v2v_prompt = gr.update(value=p)

            # Text-to-music
            if ("text to music" in seg_norm) or ("text-to-music" in seg_norm) or ("generate music" in seg_norm) or ("compose music" in seg_norm):
                upd_t2m_toggle = gr.update(value=True)
                p = after_colon(seg)
                if p:
                    upd_t2m_prompt = gr.update(value=p)

            # Image+Video-to-Animation
            if ("animate" in seg_norm) or ("character animation" in seg_norm) or ("wan animate" in seg_norm):
                upd_iv2a_toggle = gr.update(value=True)
                # Check for mode specification
                if "move mode" in seg_norm:
                    upd_anim_mode = gr.update(value="wan2.2-animate-move")
                elif "mix mode" in seg_norm:
                    upd_anim_mode = gr.update(value="wan2.2-animate-mix")
                # Check for quality specification
                if "standard quality" in seg_norm or "std quality" in seg_norm:
                    upd_anim_quality = gr.update(value="wan-std")
                elif "professional quality" in seg_norm or "pro quality" in seg_norm:
                    upd_anim_quality = gr.update(value="wan-pro")

            # URL (website redesign)
            url = _extract_url(seg)
            if url:
                upd_url = gr.update(value=url)

            # Model selection
            if "model " in seg_norm:
                try:
                    model_name = seg.split("model", 1)[1].strip()
                except Exception:
                    model_name = ""
                if model_name:
                    model_obj = _find_model_by_name(model_name)
                    if model_obj is not None:
                        upd_model_dropdown = gr.update(value=model_obj["name"])  # keep dropdown in sync
                        upd_current_model = model_obj  # pass directly to State for immediate effect

        # Files: attach first non-image/video to file_input; image to generation_image_input; video to video_input
        img_assigned = False
        video_assigned = False
        non_media_assigned = False
        for f in files:
            try:
                path = f["path"] if isinstance(f, dict) and "path" in f else f
            except Exception:
                path = None
            if not path:
                continue
            if not img_assigned and any(str(path).lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tiff", ".tif"]):
                upd_image_for_gen = gr.update(value=path)
                img_assigned = True
            elif not video_assigned and any(str(path).lower().endswith(ext) for ext in [".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v"]):
                upd_video_input = gr.update(value=path)
                video_assigned = True
            elif not non_media_assigned:
                upd_file = gr.update(value=path)
                non_media_assigned = True

        # Set main build intent from first segment (if present), otherwise full text
        if main_prompt:
            upd_input = gr.update(value=main_prompt)

        # Build assistant acknowledgement
        ack = "Configured. Running generation with your latest instructions."
        if not chat_messages:
            chat_messages = []
        chat_messages.append({"role": "user", "content": text})
        chat_messages.append({"role": "assistant", "content": ack})

        return (
            "",
            gr.update(value=chat_messages, visible=True),
            upd_input,
            upd_language,
            upd_url,
            upd_file,
            upd_image_for_gen,
            upd_search,
            upd_img_gen,
            upd_t2i_prompt,
            upd_i2i_toggle,
            upd_i2i_prompt,
            upd_i2v_toggle,
            upd_i2v_prompt,
            upd_t2v_toggle,
            upd_t2v_prompt,
            upd_v2v_toggle,
            upd_v2v_prompt,
            upd_video_input,
            upd_model_dropdown,
            upd_current_model,
            upd_t2m_toggle,
            upd_t2m_prompt,
            upd_iv2a_toggle,
            upd_anim_mode,
            upd_anim_quality,
            upd_anim_video,
        )

    # Wire chat submit -> apply settings -> run generation
    sidebar_msg.submit(
        apply_chat_command,
        inputs=[sidebar_msg, sidebar_chatbot],
        outputs=[
            sidebar_msg,
            sidebar_chatbot,
            input,
            language_dropdown,
            website_url_input,
            file_input,
            generation_image_input,
            search_toggle,
            image_generation_toggle,
            text_to_image_prompt,
            image_to_image_toggle,
            image_to_image_prompt,
            image_to_video_toggle,
            image_to_video_prompt,
            text_to_video_toggle,
            text_to_video_prompt,
            video_to_video_toggle,
            video_to_video_prompt,
            video_input,
            model_dropdown,
            current_model,
            text_to_music_toggle,
            text_to_music_prompt,
            image_video_to_animation_toggle,
            animation_mode_dropdown,
            animation_quality_dropdown,
            animation_video_input,
        ],
        queue=False,
    ).then(
        begin_generation_ui,
        inputs=None,
        outputs=[sidebar, generating_status],
        show_progress="hidden",
    ).then(
        generation_code,
        inputs=[input, image_input, generation_image_input, file_input, website_url_input, setting, history, current_model, search_toggle, language_dropdown, provider_state, image_generation_toggle, image_to_image_toggle, image_to_image_prompt, text_to_image_prompt, image_to_video_toggle, image_to_video_prompt, text_to_video_toggle, text_to_video_prompt, video_to_video_toggle, video_to_video_prompt, video_input, text_to_music_toggle, text_to_music_prompt, image_video_to_animation_toggle, animation_mode_dropdown, animation_quality_dropdown, animation_video_input],
        outputs=[code_output, history, sandbox, history_output]
    ).then(
        end_generation_ui,
        inputs=None,
        outputs=[sidebar, generating_status]
    ).then(
        toggle_editors,
        inputs=[language_dropdown, code_output],
        outputs=[code_output, tjs_group, tjs_html_code, tjs_js_code, tjs_css_code]
    ).then(
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
        show_deploy_components,
        None,
        [space_name_input, sdk_dropdown, deploy_btn]
    ).then(
        preserve_space_info_for_followup,
        inputs=[history],
        outputs=[space_name_input, deploy_btn]
    )

    # Toggle between classic controls and beta chat UI
    def toggle_beta(checked: bool, t2i: bool, i2i: bool, i2v: bool, t2v: bool, v2v: bool, t2m: bool, iv2a: bool):
        # Prompts only visible in classic mode and when their toggles are on
        t2i_vis = (not checked) and bool(t2i)
        i2i_vis = (not checked) and bool(i2i)
        i2v_vis = (not checked) and bool(i2v)
        t2v_vis = (not checked) and bool(t2v)
        v2v_vis = (not checked) and bool(v2v)
        t2m_vis = (not checked) and bool(t2m)
        iv2a_vis = (not checked) and bool(iv2a)

        return (
            # Chat UI group
            gr.update(visible=checked),  # sidebar_chatbot
            gr.update(visible=checked),  # sidebar_msg
            gr.update(visible=checked),  # advanced_commands
            gr.update(visible=checked),  # chat_clear_btn
            # Classic controls
            gr.update(visible=not checked),  # input
            gr.update(visible=not checked),  # language_dropdown
            gr.update(visible=not checked),  # website_url_input
            gr.update(visible=not checked),  # file_input
            gr.update(visible=not checked),  # btn
            gr.update(visible=not checked),  # clear_btn
            gr.update(visible=not checked),  # search_toggle
            gr.update(visible=not checked),  # image_generation_toggle
            gr.update(visible=t2i_vis),      # text_to_image_prompt
            gr.update(visible=not checked),  # image_to_image_toggle
            gr.update(visible=i2i_vis),      # image_to_image_prompt
            gr.update(visible=not checked),  # image_to_video_toggle
            gr.update(visible=i2v_vis),      # image_to_video_prompt
            gr.update(visible=not checked),  # text_to_video_toggle
            gr.update(visible=t2v_vis),      # text_to_video_prompt
            gr.update(visible=not checked),  # video_to_video_toggle
            gr.update(visible=v2v_vis),      # video_to_video_prompt
            gr.update(visible=v2v_vis),      # video_input
            gr.update(visible=not checked),  # text_to_music_toggle
            gr.update(visible=t2m_vis),      # text_to_music_prompt
            gr.update(visible=not checked),  # image_video_to_animation_toggle
            gr.update(visible=iv2a_vis),     # animation_mode_dropdown
            gr.update(visible=iv2a_vis),     # animation_quality_dropdown
            gr.update(visible=iv2a_vis),     # animation_video_input
            gr.update(visible=not checked),  # model_dropdown
            gr.update(visible=not checked),  # quick_start_md
            gr.update(visible=not checked),  # quick_examples_col
        )

    beta_toggle.change(
        toggle_beta,
        inputs=[beta_toggle, image_generation_toggle, image_to_image_toggle, image_to_video_toggle, text_to_video_toggle, video_to_video_toggle, text_to_music_toggle, image_video_to_animation_toggle],
        outputs=[
            sidebar_chatbot,
            sidebar_msg,
            advanced_commands,
            chat_clear_btn,
            input,
            language_dropdown,
            website_url_input,
            file_input,
            btn,
            clear_btn,
            search_toggle,
            image_generation_toggle,
            text_to_image_prompt,
            image_to_image_toggle,
            image_to_image_prompt,
            image_to_video_toggle,
            image_to_video_prompt,
            text_to_video_toggle,
            text_to_video_prompt,
            video_to_video_toggle,
            video_to_video_prompt,
            video_input,
            text_to_music_toggle,
            text_to_music_prompt,
            image_video_to_animation_toggle,
            animation_mode_dropdown,
            animation_quality_dropdown,
            animation_video_input,
            model_dropdown,
            quick_start_md,
            quick_examples_col,
        ],
    )
    # Update preview when code or language changes (supports multi-file path via optional args)
    code_output.change(preview_logic, inputs=[code_output, language_dropdown, tjs_html_code, tjs_js_code, tjs_css_code], outputs=sandbox)
    language_dropdown.change(preview_logic, inputs=[code_output, language_dropdown, tjs_html_code, tjs_js_code, tjs_css_code], outputs=sandbox)
    # Update deploy button text when space name changes
    space_name_input.change(update_deploy_button_text, inputs=[space_name_input], outputs=[deploy_btn])
    clear_btn.click(clear_history, outputs=[history, history_output, file_input, website_url_input])
    clear_btn.click(hide_deploy_components, None, [space_name_input, sdk_dropdown, deploy_btn])
    # Reset space name and button text when clearing
    clear_btn.click(
        lambda: [gr.update(value=""), gr.update(value="🚀 Deploy App")],
        outputs=[space_name_input, deploy_btn]
    )

    # Theme switching handlers
    def handle_theme_change(theme_name):
        """Handle theme selection change and update description"""
        if theme_name in THEME_CONFIGS:
            description = THEME_CONFIGS[theme_name]["description"]
            features = THEME_FEATURES.get(theme_name, [])
            feature_text = f"**Features:** {', '.join(features)}" if features else ""
            full_description = f"*{description}*\n\n{feature_text}"
            
            return gr.update(value=full_description)
        return gr.update()

    def apply_theme_change(theme_name):
        """Save theme preference and show restart instruction"""
        if theme_name in THEME_CONFIGS:
            save_theme_preference(theme_name)
            
            restart_message = f"""
🎨 **Theme saved:** {theme_name}
⚠️ **Restart required** to fully apply the new theme.

**Why restart is needed:** Gradio themes are set during application startup and cannot be changed dynamically at runtime. This ensures all components are properly styled with consistent theming.

**To apply your new theme:**
1. Stop the application (Ctrl+C)
2. Restart it with the same command
3. Your theme will be automatically loaded

*Your theme preference has been saved and will persist across restarts.*
            """
            
            return gr.update(value=restart_message, visible=True, elem_classes=["restart-needed"])
        return gr.update()

    # Theme dropdown change event  
    theme_dropdown.change(
        handle_theme_change,
        inputs=[theme_dropdown],
        outputs=[theme_description]
    )
    
    # Apply theme button click event
    apply_theme_btn.click(
        apply_theme_change,
        inputs=[theme_dropdown],
        outputs=[theme_status]
    )

    # Deploy to Spaces logic

    def deploy_to_user_space(
        code, 
        space_name, 
        sdk_name,  # new argument
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
        
        # Check if this is an update to an existing space (contains /)
        is_update = "/" in space_name.strip()
        if is_update:
            # This is an existing space, use the provided space_name as repo_id
            repo_id = space_name.strip()
            # Extract username from repo_id for permission check
            space_username = repo_id.split('/')[0]
            if space_username != profile.username:
                return gr.update(value=f"Error: You can only update your own spaces. This space belongs to {space_username}.", visible=True)
            
            # Verify the user has write access to this space
            try:
                api = HfApi(token=token.token)
                # Try to get space info to verify access
                space_info = api.space_info(repo_id)
                if not space_info:
                    return gr.update(value=f"Error: Could not access space {repo_id}. Please check your permissions.", visible=True)
            except Exception as e:
                return gr.update(value=f"Error: No write access to space {repo_id}. Please ensure you have the correct permissions. Error: {str(e)}", visible=True)
        else:
            # This is a new space, create repo_id with current user
            username = profile.username
            repo_id = f"{username}/{space_name.strip()}"
        # Map SDK name to HF SDK slug
        sdk_map = {
            "Gradio (Python)": "gradio",
            "Streamlit (Python)": "docker",  # Use 'docker' for Streamlit Spaces
            "Static (HTML)": "static",
            "Transformers.js": "static",  # Transformers.js uses static SDK
            "Svelte": "static"  # Svelte uses static SDK
        }
        sdk = sdk_map.get(sdk_name, "gradio")
        
        # Create API client with user's token for proper authentication
        api = HfApi(token=token.token)
        # Only create the repo for new spaces (not updates) and non-Transformers.js, non-Streamlit, and non-Svelte SDKs
        if not is_update and sdk != "docker" and sdk_name not in ["Transformers.js", "Svelte"]:
            try:
                api.create_repo(
                    repo_id=repo_id,  # e.g. username/space_name
                    repo_type="space",
                    space_sdk=sdk,  # Use selected SDK
                    exist_ok=True  # Don't error if it already exists
                )
            except Exception as e:
                return gr.update(value=f"Error creating Space: {e}", visible=True)
        # Streamlit/docker logic
        if sdk == "docker":
            try:
                # For new spaces, duplicate the template first
                if not is_update:
                    # Use duplicate_space to create a Streamlit template space
                    from huggingface_hub import duplicate_space
                    
                    # Duplicate the streamlit template space
                    duplicated_repo = duplicate_space(
                        from_id="streamlit/streamlit-template-space",
                        to_id=space_name.strip(),
                        token=token.token,
                        exist_ok=True
                    )
                
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
        elif sdk_name == "Transformers.js":
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
        # Svelte logic
        elif sdk_name == "Svelte":
            try:
                actual_repo_id = repo_id
                # For new spaces, duplicate the template first
                if not is_update:
                    from huggingface_hub import duplicate_space
                    import time
                    duplicated_repo = duplicate_space(
                        from_id="static-templates/svelte",
                        to_id=repo_id,
                        token=token.token,
                        exist_ok=True
                    )
                    print("Duplicated Svelte repo result:", duplicated_repo, type(duplicated_repo))
                    # Extract the actual repo ID from the duplicated space (RepoUrl)
                    try:
                        duplicated_repo_str = str(duplicated_repo)
                        if "/spaces/" in duplicated_repo_str:
                            parts = duplicated_repo_str.split("/spaces/")[-1].split("/")
                            if len(parts) >= 2:
                                actual_repo_id = f"{parts[0]}/{parts[1]}"
                    except Exception as e:
                        print(f"Error extracting repo ID from duplicated_repo: {e}")
                        actual_repo_id = repo_id
                    
                    # Small delay to allow the duplication to fully complete and reduce race conditions
                    print("Waiting for template duplication to complete...")
                    time.sleep(3)
                    
                print("Actual repo ID for Svelte uploads:", actual_repo_id)

                # Parse all generated Svelte files (dynamic multi-file)
                files = parse_svelte_output(code) or {}
                if not isinstance(files, dict) or 'src/App.svelte' not in files or not files['src/App.svelte'].strip():
                    return gr.update(value="Error: Could not parse Svelte output (missing src/App.svelte). Please regenerate the code.", visible=True)

                # Validate that src/main.ts is generated (should be required now)
                if 'src/main.ts' not in files:
                    return gr.update(value="Error: Missing src/main.ts file. Please regenerate the code to include the main entry point.", visible=True)

                # Ensure package.json includes any external npm deps used; overwrite template's package.json
                try:
                    detected = infer_svelte_dependencies(files)
                    existing_pkg_text = files.get('package.json')
                    pkg_text = build_svelte_package_json(existing_pkg_text, detected)
                    # Only write if we have either detected deps or user provided a package.json
                    if pkg_text and (detected or existing_pkg_text is not None):
                        files['package.json'] = pkg_text
                except Exception as e:
                    # Non-fatal: proceed without generating package.json
                    print(f"[Svelte Deploy] package.json synthesis skipped: {e}")

                # Write all files to a temp directory and upload folder in one commit
                import tempfile, os, time
                with tempfile.TemporaryDirectory() as tmpdir:
                    for rel_path, content in files.items():
                        safe_rel = (rel_path or '').strip().lstrip('/')
                        abs_path = os.path.join(tmpdir, safe_rel)
                        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                        with open(abs_path, 'w') as fh:
                            fh.write(content or '')
                    
                    # Retry logic for upload_folder to handle race conditions
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            api.upload_folder(
                                folder_path=tmpdir,
                                repo_id=actual_repo_id,
                                repo_type="space"
                            )
                            break  # Success, exit retry loop
                        except Exception as upload_error:
                            if "commit has happened since" in str(upload_error).lower() and attempt < max_retries - 1:
                                print(f"Svelte upload attempt {attempt + 1} failed due to race condition, retrying in 2 seconds...")
                                time.sleep(2)  # Wait before retry
                                continue
                            else:
                                raise upload_error  # Re-raise if not a race condition or max retries reached

                # Add anycoder tag to existing README (with retry logic)
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        add_anycoder_tag_to_readme(api, actual_repo_id)
                        break  # Success, exit retry loop
                    except Exception as readme_error:
                        if "commit has happened since" in str(readme_error).lower() and attempt < max_retries - 1:
                            print(f"README tag attempt {attempt + 1} failed due to race condition, retrying in 2 seconds...")
                            time.sleep(2)  # Wait before retry
                            continue
                        else:
                            # Non-fatal: README tagging is not critical, just log and continue
                            print(f"Failed to add anycoder tag to README after {max_retries} attempts: {readme_error}")
                            break

                # Success
                space_url = f"https://huggingface.co/spaces/{actual_repo_id}"
                action_text = "Updated" if is_update else "Deployed"
                return gr.update(value=f"✅ {action_text}! [Open your Svelte Space here]({space_url})", visible=True)

            except Exception as e:
                error_msg = str(e)
                return gr.update(value=f"Error deploying Svelte app: {error_msg}", visible=True)
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
                
                # Upload temporary media files to HF and replace URLs (only for Static HTML, not Transformers.js)
                if sdk == "static" and sdk_name == "Static (HTML)":
                    print("[Deploy] Uploading temporary media files to HF and updating URLs for multi-file static HTML app")
                    # Update the index.html file with permanent media URLs
                    if 'index.html' in files:
                        files['index.html'] = upload_temp_files_to_hf_and_replace_urls(files['index.html'], token)
                
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
            
            # Upload temporary media files to HF and replace URLs (only for Static HTML, not Transformers.js)
            if sdk == "static" and sdk_name == "Static (HTML)":
                print("[Deploy] Uploading temporary media files to HF and updating URLs for single-file static HTML app")
                code = upload_temp_files_to_hf_and_replace_urls(code, token)
            
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
            
            # Now upload the main app.py file
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
        deploy_to_user_space,
        inputs=[code_output, space_name_input, sdk_dropdown],
        outputs=deploy_status
    )
    # Keep the old deploy method as fallback (if not logged in, user can still use the old method)
    # Optionally, you can keep the old deploy_btn.click for the default method as a secondary button.

if __name__ == "__main__":
    # Initialize Gradio documentation system
    initialize_gradio_docs()
    
    # Clean up any orphaned temporary files from previous runs
    cleanup_all_temp_media_on_startup()
    
    demo.queue(api_open=False, default_concurrency_limit=20).launch(
        show_api=False, 
        ssr_mode=True, 
        mcp_server=False
    )