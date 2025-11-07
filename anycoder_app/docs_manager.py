"""
Documentation management for Gradio, ComfyUI, and FastRTC.
Handles fetching, caching, and updating documentation from llms.txt files.
"""
import os
import requests
import re
from datetime import datetime, timedelta
from typing import Optional

from .config import (
    GRADIO_LLMS_TXT_URL, GRADIO_DOCS_CACHE_FILE, GRADIO_DOCS_LAST_UPDATE_FILE,
    GRADIO_DOCS_UPDATE_ON_APP_UPDATE, _gradio_docs_content, _gradio_docs_last_fetched,
    COMFYUI_LLMS_TXT_URL, COMFYUI_DOCS_CACHE_FILE, COMFYUI_DOCS_LAST_UPDATE_FILE,
    COMFYUI_DOCS_UPDATE_ON_APP_UPDATE, _comfyui_docs_content, _comfyui_docs_last_fetched,
    FASTRTC_LLMS_TXT_URL, FASTRTC_DOCS_CACHE_FILE, FASTRTC_DOCS_LAST_UPDATE_FILE,
    FASTRTC_DOCS_UPDATE_ON_APP_UPDATE, _fastrtc_docs_content, _fastrtc_docs_last_fetched
)
from . import prompts

def fetch_gradio_docs() -> Optional[str]:
    """Fetch the latest Gradio documentation from llms.txt"""
    try:
        response = requests.get(GRADIO_LLMS_TXT_URL, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Warning: Failed to fetch Gradio docs from {GRADIO_LLMS_TXT_URL}: {e}")
        return None

def fetch_comfyui_docs() -> Optional[str]:
    """Fetch the latest ComfyUI documentation from llms.txt"""
    try:
        response = requests.get(COMFYUI_LLMS_TXT_URL, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Warning: Failed to fetch ComfyUI docs from {COMFYUI_LLMS_TXT_URL}: {e}")
        return None

def fetch_fastrtc_docs() -> Optional[str]:
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

def load_comfyui_docs_cache() -> Optional[str]:
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

def load_fastrtc_docs_cache() -> Optional[str]:
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
    docs_content = get_gradio_docs_content()
    fastrtc_content = get_fastrtc_docs_content()
    
    # Base system prompt
    base_prompt = """You are an expert Gradio developer. Create a complete, working Gradio application based on the user's request. Generate all necessary code to make the application functional and runnable.

🚨 CRITICAL OUTPUT RULES:
- DO NOT use <think> tags or thinking blocks in your output
- DO NOT use [TOOL_CALL] or any tool call markers
- Generate ONLY the requested code files and requirements.txt
- No explanatory text outside the code blocks

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
    
    # Update the prompts in the prompts module
    prompts.GRADIO_SYSTEM_PROMPT = base_prompt + docs_content + "\n\nAlways use the exact function signatures from this API reference and follow modern Gradio patterns.\n\nIMPORTANT: Always include \"Built with anycoder\" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder"
    prompts.GRADIO_SYSTEM_PROMPT_WITH_SEARCH = search_prompt + docs_content + "\n\nAlways use the exact function signatures from this API reference and follow modern Gradio patterns.\n\nIMPORTANT: Always include \"Built with anycoder\" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder"

def update_json_system_prompts():
    """Update the global JSON system prompts with latest ComfyUI documentation"""
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
    
    # Update the prompts in the prompts module
    prompts.JSON_SYSTEM_PROMPT = base_prompt
    prompts.JSON_SYSTEM_PROMPT_WITH_SEARCH = search_prompt

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

