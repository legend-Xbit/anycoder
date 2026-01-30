"""
Documentation management for backend system prompts.
Handles fetching, caching, and updating documentation from llms.txt files.
No dependencies on Gradio or other heavy libraries - pure Python only.
"""
import os
import re
from datetime import datetime
from typing import Optional

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("Warning: requests library not available, using minimal fallback")

# Configuration
GRADIO_LLMS_TXT_URL = "https://www.gradio.app/llms.txt"
GRADIO_DOCS_CACHE_FILE = ".backend_gradio_docs_cache.txt"
GRADIO_DOCS_LAST_UPDATE_FILE = ".backend_gradio_docs_last_update.txt"

TRANSFORMERSJS_DOCS_URL = "https://huggingface.co/docs/transformers.js/llms.txt"
TRANSFORMERSJS_DOCS_CACHE_FILE = ".backend_transformersjs_docs_cache.txt"
TRANSFORMERSJS_DOCS_LAST_UPDATE_FILE = ".backend_transformersjs_docs_last_update.txt"

COMFYUI_LLMS_TXT_URL = "https://docs.comfy.org/llms.txt"
COMFYUI_DOCS_CACHE_FILE = ".backend_comfyui_docs_cache.txt"
COMFYUI_DOCS_LAST_UPDATE_FILE = ".backend_comfyui_docs_last_update.txt"

# Global variable to store the current Gradio documentation
_gradio_docs_content: Optional[str] = None
_gradio_docs_last_fetched: Optional[datetime] = None

# Global variable to store the current transformers.js documentation
_transformersjs_docs_content: Optional[str] = None
_transformersjs_docs_last_fetched: Optional[datetime] = None

# Global variable to store the current ComfyUI documentation
_comfyui_docs_content: Optional[str] = None
_comfyui_docs_last_fetched: Optional[datetime] = None

def fetch_gradio_docs() -> Optional[str]:
    """Fetch the latest Gradio documentation from llms.txt"""
    if not HAS_REQUESTS:
        return None
    
    try:
        response = requests.get(GRADIO_LLMS_TXT_URL, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Warning: Failed to fetch Gradio docs from {GRADIO_LLMS_TXT_URL}: {e}")
        return None

def fetch_transformersjs_docs() -> Optional[str]:
    """Fetch the latest transformers.js documentation from llms.txt"""
    if not HAS_REQUESTS:
        return None
    
    try:
        response = requests.get(TRANSFORMERSJS_DOCS_URL, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Warning: Failed to fetch transformers.js docs from {TRANSFORMERSJS_DOCS_URL}: {e}")
        return None

def fetch_comfyui_docs() -> Optional[str]:
    """Fetch the latest ComfyUI documentation from llms.txt"""
    if not HAS_REQUESTS:
        return None
    
    try:
        response = requests.get(COMFYUI_LLMS_TXT_URL, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Warning: Failed to fetch ComfyUI docs from {COMFYUI_LLMS_TXT_URL}: {e}")
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

def should_update_gradio_docs() -> bool:
    """Check if Gradio documentation should be updated"""
    # Only update if we don't have cached content (first run or cache deleted)
    return not os.path.exists(GRADIO_DOCS_CACHE_FILE)

def load_cached_transformersjs_docs() -> Optional[str]:
    """Load cached transformers.js documentation from file"""
    try:
        if os.path.exists(TRANSFORMERSJS_DOCS_CACHE_FILE):
            with open(TRANSFORMERSJS_DOCS_CACHE_FILE, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        print(f"Warning: Failed to load cached transformers.js docs: {e}")
    return None

def save_transformersjs_docs_cache(content: str):
    """Save transformers.js documentation to cache file"""
    try:
        with open(TRANSFORMERSJS_DOCS_CACHE_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        with open(TRANSFORMERSJS_DOCS_LAST_UPDATE_FILE, 'w', encoding='utf-8') as f:
            f.write(datetime.now().isoformat())
    except Exception as e:
        print(f"Warning: Failed to save transformers.js docs cache: {e}")

def should_update_transformersjs_docs() -> bool:
    """Check if transformers.js documentation should be updated"""
    # Only update if we don't have cached content (first run or cache deleted)
    return not os.path.exists(TRANSFORMERSJS_DOCS_CACHE_FILE)

def load_cached_comfyui_docs() -> Optional[str]:
    """Load cached ComfyUI documentation from file"""
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

def should_update_comfyui_docs() -> bool:
    """Check if ComfyUI documentation should be updated"""
    # Only update if we don't have cached content (first run or cache deleted)
    return not os.path.exists(COMFYUI_DOCS_CACHE_FILE)

def get_gradio_docs_content() -> str:
    """Get the current Gradio documentation content, updating if necessary"""
    global _gradio_docs_content, _gradio_docs_last_fetched
    
    # Check if we need to update
    if (_gradio_docs_content is None or 
        _gradio_docs_last_fetched is None or 
        should_update_gradio_docs()):
        
        print("📚 Loading Gradio 6 documentation...")
        
        # Try to fetch latest content
        latest_content = fetch_gradio_docs()
        
        if latest_content:
            # Filter out problematic instructions that cause early termination
            filtered_content = filter_problematic_instructions(latest_content)
            _gradio_docs_content = filtered_content
            _gradio_docs_last_fetched = datetime.now()
            save_gradio_docs_cache(filtered_content)
            print(f"✅ Gradio 6 documentation loaded successfully ({len(filtered_content)} chars)")
        else:
            # Fallback to cached content
            cached_content = load_cached_gradio_docs()
            if cached_content:
                _gradio_docs_content = cached_content
                _gradio_docs_last_fetched = datetime.now()
                print(f"⚠️ Using cached Gradio documentation (network fetch failed) ({len(cached_content)} chars)")
            else:
                # Fallback to minimal content
                _gradio_docs_content = """
# Gradio API Reference (Offline Fallback)

This is a minimal fallback when documentation cannot be fetched.
Please check your internet connection for the latest API reference.

Basic Gradio components: Button, Textbox, Slider, Image, Audio, Video, File, etc.
Use gr.Blocks() for custom layouts and gr.Interface() for simple apps.

For the latest documentation, visit: https://www.gradio.app/llms.txt
"""
                print("❌ Using minimal fallback documentation")
    
    return _gradio_docs_content or ""

def get_transformersjs_docs_content() -> str:
    """Get the current transformers.js documentation content, updating if necessary"""
    global _transformersjs_docs_content, _transformersjs_docs_last_fetched
    
    # Check if we need to update
    if (_transformersjs_docs_content is None or 
        _transformersjs_docs_last_fetched is None or 
        should_update_transformersjs_docs()):
        
        print("📚 Loading transformers.js documentation...")
        
        # Try to fetch latest content
        latest_content = fetch_transformersjs_docs()
        
        if latest_content:
            # Filter out problematic instructions that cause early termination
            filtered_content = filter_problematic_instructions(latest_content)
            _transformersjs_docs_content = filtered_content
            _transformersjs_docs_last_fetched = datetime.now()
            save_transformersjs_docs_cache(filtered_content)
            print(f"✅ transformers.js documentation loaded successfully ({len(filtered_content)} chars)")
        else:
            # Fallback to cached content
            cached_content = load_cached_transformersjs_docs()
            if cached_content:
                _transformersjs_docs_content = cached_content
                _transformersjs_docs_last_fetched = datetime.now()
                print(f"⚠️ Using cached transformers.js documentation (network fetch failed) ({len(cached_content)} chars)")
            else:
                # Fallback to minimal content
                _transformersjs_docs_content = """
# Transformers.js API Reference (Offline Fallback)

This is a minimal fallback when documentation cannot be fetched.
Please check your internet connection for the latest API reference.

Transformers.js allows you to run 🤗 Transformers models directly in the browser using ONNX Runtime.

Key features:
- pipeline() API for common tasks (sentiment-analysis, text-generation, etc.)
- Support for custom models via model ID or path
- WebGPU support for GPU acceleration
- Quantization support (fp32, fp16, q8, q4)

Basic usage:
```javascript
import { pipeline } from '@huggingface/transformers';
const pipe = await pipeline('sentiment-analysis');
const out = await pipe('I love transformers!');
```

For the latest documentation, visit: https://huggingface.co/docs/transformers.js
"""
                print("❌ Using minimal fallback transformers.js documentation")
    
    return _transformersjs_docs_content or ""

def get_comfyui_docs_content() -> str:
    """Get the current ComfyUI documentation content, updating if necessary"""
    global _comfyui_docs_content, _comfyui_docs_last_fetched
    
    # Check if we need to update
    if (_comfyui_docs_content is None or 
        _comfyui_docs_last_fetched is None or 
        should_update_comfyui_docs()):
        
        print("📚 Loading ComfyUI documentation...")
        
        # Try to fetch latest content
        latest_content = fetch_comfyui_docs()
        
        if latest_content:
            # Filter out problematic instructions that cause early termination
            filtered_content = filter_problematic_instructions(latest_content)
            _comfyui_docs_content = filtered_content
            _comfyui_docs_last_fetched = datetime.now()
            save_comfyui_docs_cache(filtered_content)
            print(f"✅ ComfyUI documentation loaded successfully ({len(filtered_content)} chars)")
        else:
            # Fallback to cached content
            cached_content = load_cached_comfyui_docs()
            if cached_content:
                _comfyui_docs_content = cached_content
                _comfyui_docs_last_fetched = datetime.now()
                print(f"⚠️ Using cached ComfyUI documentation (network fetch failed) ({len(cached_content)} chars)")
            else:
                # Fallback to minimal content
                _comfyui_docs_content = """
# ComfyUI API Reference (Offline Fallback)

This is a minimal fallback when documentation cannot be fetched.
Please check your internet connection for the latest API reference.

Basic ComfyUI workflow structure: nodes, connections, inputs, outputs.
Use CheckpointLoaderSimple, CLIPTextEncode, KSampler for basic workflows.

For the latest documentation, visit: https://docs.comfy.org/llms.txt
"""
                print("❌ Using minimal fallback ComfyUI documentation")
    
    return _comfyui_docs_content or ""

def build_gradio_system_prompt() -> str:
    """Build the complete Gradio system prompt with full documentation"""
    
    # Get the full Gradio 6 documentation
    docs_content = get_gradio_docs_content()
    
    # Base system prompt with anycoder-specific instructions
    base_prompt = """🚨 CRITICAL: You are an expert Gradio 6 developer. You MUST use Gradio 6 syntax and API.

## Key Gradio 6 Changes (MUST FOLLOW):
- 🚨 **BREAKING CHANGE**: `theme`, `css`, `js`, `head` parameters moved from `gr.Blocks()` to `demo.launch()`
- 🚨 **gr.Blocks() has NO parameters** - use `with gr.Blocks() as demo:` (no args!)
- 🚨 **ALL app-level params go in demo.launch()**: `theme=`, `css=`, `footer_links=`, etc.
- Use `footer_links` parameter in `demo.launch()` (NOT show_api)
- Use `api_visibility` instead of `api_name` in event listeners
- Use modern Gradio 6 component syntax (check documentation below)
- Gradio 6 has updated component APIs - always refer to the documentation below
- DO NOT use deprecated Gradio 5 or older syntax

Create a complete, working Gradio 6 application based on the user's request. Generate all necessary code to make the application functional and runnable.

## Gradio 6 Themes (Modern UI Design):

Gradio 6 provides powerful theming capabilities. Use themes to create beautiful, professional interfaces:

**Built-in Themes:**
```python
import gradio as gr

# Use predefined themes in launch() - Gradio 6 syntax
with gr.Blocks() as demo:
    gr.Textbox(label="Input")

demo.launch(theme=gr.themes.Soft())  # Soft, rounded design
# demo.launch(theme=gr.themes.Glass())  # Modern glass morphism
# demo.launch(theme=gr.themes.Monochrome())  # Clean monochrome
# demo.launch(theme=gr.themes.Base())  # Default base theme
```

**Custom Themes:**
```python
import gradio as gr

# Create custom theme
custom_theme = gr.themes.Soft(
    primary_hue="blue",
    secondary_hue="indigo",
    neutral_hue="slate",
    font=gr.themes.GoogleFont("Inter"),
    text_size="lg",
    spacing_size="lg",
    radius_size="md"
).set(
    button_primary_background_fill="*primary_600",
    button_primary_background_fill_hover="*primary_700",
    block_title_text_weight="600",
)

with gr.Blocks() as demo:
    gr.Textbox(label="Input")

demo.launch(theme=custom_theme)  # Apply theme in launch() - Gradio 6!
```

**Best Practices:**
- 🚨 **CRITICAL**: In Gradio 6, `theme` goes in `demo.launch()`, NOT in `gr.Blocks()`
- Use `gr.themes.Soft()` for modern, friendly apps
- Use `gr.themes.Glass()` for sleek, contemporary designs
- Customize colors with `primary_hue`, `secondary_hue`, `neutral_hue`
- Use Google Fonts: `font=gr.themes.GoogleFont("Roboto")`
- Adjust sizing: `text_size`, `spacing_size`, `radius_size` (sm/md/lg)
- Fine-tune with `.set()` for specific CSS variables

## Gradio 6 Example (Your Code Should Follow This Pattern):

```python
import gradio as gr

def process(text):
    return f"Processed: {text}"

# Gradio 6 - NO parameters in gr.Blocks() constructor!
with gr.Blocks() as demo:
    gr.Markdown("# My App")
    with gr.Row():
        input_text = gr.Textbox(label="Input")
        output_text = gr.Textbox(label="Output")
    
    btn = gr.Button("Process")
    
    # Gradio 6 events use api_visibility (NOT just api_name)
    btn.click(
        fn=process,
        inputs=[input_text],
        outputs=[output_text],
        api_visibility="public"  # Gradio 6 syntax
    )

# Gradio 6 - ALL app parameters go in launch()!
demo.launch(
    theme=gr.themes.Soft(primary_hue="blue"),
    footer_links=[{"label": "Built with anycoder", "url": "https://huggingface.co/spaces/akhaliq/anycoder"}]
)
```

## Multi-File Application Structure

When creating Gradio applications, organize your code into multiple files for proper deployment:

**File Organization:**
- `app.py` - Main application entry point (REQUIRED)
- `requirements.txt` - Python dependencies (REQUIRED, auto-generated from imports). ALWAYS use `daggr>=0.5.4` and `gradio>=6.0.2` if applicable.
- `utils.py` - Utility functions and helpers (optional)
- `models.py` - Model loading and inference functions (optional)
- `config.py` - Configuration and constants (optional)

**Output Format:**
You MUST use this exact format with file separators:

=== app.py ===
[complete app.py content]

=== utils.py ===
[utility functions - if needed]

**🚨 CRITICAL: DO NOT GENERATE requirements.txt or README.md**
- requirements.txt is automatically generated from your app.py imports
- README.md is automatically provided by the template
- Generating these files will break the deployment process

Requirements:
1. Create a modern, intuitive Gradio application
2. Use appropriate Gradio components (gr.Textbox, gr.Slider, etc.)
3. Include proper error handling and loading states
4. Use gr.Interface or gr.Blocks as appropriate
5. Add helpful descriptions and examples
6. Follow Gradio best practices
7. Make the UI user-friendly with clear labels
8. Include proper documentation in docstrings

IMPORTANT: Always include "Built with anycoder" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder

---

## Complete Gradio 6 Documentation

Below is the complete, official Gradio 6 documentation automatically synced from https://www.gradio.app/llms.txt:

"""
    
    # Combine base prompt with full documentation
    full_prompt = base_prompt + docs_content
    
    # Add final instructions
    final_instructions = """

---

## 🚨 CRITICAL FINAL INSTRUCTIONS - GRADIO 6 ONLY

YOU MUST USE GRADIO 6 SYNTAX. This is MANDATORY:

1. **ONLY use Gradio 6 API** - Do NOT use Gradio 5 or older syntax
2. **Reference the documentation above** - All function signatures and patterns are from Gradio 6
3. **Use modern Gradio 6 patterns:**
   - 🚨 **CRITICAL**: `theme`, `css`, `js`, `head` go in `demo.launch()`, NOT in `gr.Blocks()`
   - Use `footer_links` parameter in `demo.launch()` (NOT show_api in Blocks)
   - Use `api_visibility` in event listeners (NOT api_name alone)
   - Use updated component syntax from Gradio 6 documentation
   - **Use themes for professional UI design** (gr.themes.Soft(), gr.themes.Glass(), etc.)
4. **Always use themes** - Modern Gradio 6 apps should use `theme=gr.themes.Soft()` in `demo.launch()`
5. **Follow Gradio 6 migration guide** if you see any deprecated patterns
6. **Generate production-ready Gradio 6 code** that follows all best practices
7. **Always include "Built with anycoder"** as clickable text in the header linking to https://huggingface.co/spaces/akhaliq/anycoder

**Gradio 6 Structure Checklist:**
✅ `with gr.Blocks() as demo:` - NO parameters here!
✅ `demo.launch(theme=..., css=..., footer_links=...)` - ALL app parameters here!
✅ Use `theme=` parameter in `demo.launch()` (NOT in gr.Blocks())
✅ Choose appropriate theme: Soft (friendly), Glass (modern), Monochrome (minimal)
✅ Customize with primary_hue, font, text_size, spacing_size
✅ Use `.set()` for advanced customization

REMINDER: You are writing Gradio 6 code with modern themes. In Gradio 6, `gr.Blocks()` has NO parameters - everything goes in `demo.launch()`. Double-check all syntax against the Gradio 6 documentation provided above.

"""
    
    return full_prompt + final_instructions

def build_transformersjs_system_prompt() -> str:
    """Build the complete transformers.js system prompt with full documentation"""
    
    # Get the full transformers.js documentation
    docs_content = get_transformersjs_docs_content()
    
    # Base system prompt with anycoder-specific instructions
    base_prompt = """You are an expert transformers.js developer. Create a complete, working browser-based ML application using transformers.js based on the user's request. Generate all necessary code to make the application functional and runnable in the browser.

## Multi-File Application Structure

When creating transformers.js applications, organize your code into multiple files for proper deployment:

**File Organization:**
- `index.html` - Main HTML entry point (REQUIRED)
- `app.js` - Main JavaScript application logic (REQUIRED)
- `styles.css` - Styling (optional)
- `worker.js` - Web Worker for model loading (recommended for better performance)
- `package.json` - Node.js dependencies if using bundler (optional)

**Output Format:**
You MUST use this exact format with file separators:

=== index.html ===
[complete HTML content]

=== app.js ===
[complete JavaScript content]

=== worker.js ===
[web worker content - if needed]

**🚨 CRITICAL: Best Practices**
- Use CDN for transformers.js: https://cdn.jsdelivr.net/npm/@huggingface/transformers
- Implement loading states and progress indicators
- Use Web Workers for model loading to avoid blocking UI
- Handle errors gracefully with user-friendly messages
- Show model download progress when applicable
- Use quantized models (q8, q4) for faster loading in browser

Requirements:
1. Create a modern, responsive web application
2. Use appropriate transformers.js pipelines and models
3. Include proper error handling and loading states
4. Implement progress indicators for model loading
5. Add helpful descriptions and examples
6. Follow browser best practices (async/await, Web Workers, etc.)
7. Make the UI user-friendly with clear labels
8. Include proper comments in code

IMPORTANT: Always include "Built with anycoder" as clickable text in the header/top section of your application that links to https://huggingface.co/spaces/akhaliq/anycoder

---

## Complete transformers.js Documentation

Below is the complete, official transformers.js documentation automatically synced from https://huggingface.co/docs/transformers.js/llms.txt:

"""
    
    # Combine base prompt with full documentation
    full_prompt = base_prompt + docs_content
    
    # Add final instructions
    final_instructions = """

---

## Final Instructions

- Always use the exact function signatures and patterns from the transformers.js documentation above
- Use the pipeline() API for common tasks
- Implement WebGPU support when appropriate for better performance
- Use quantized models by default (q8 or q4) for faster browser loading
- Generate production-ready code that follows all best practices
- Always include the "Built with anycoder" attribution in the header
- Consider using Web Workers for heavy computation to keep UI responsive

"""
    
    return full_prompt + final_instructions

def build_comfyui_system_prompt() -> str:
    """Build the complete ComfyUI system prompt with full documentation"""
    
    # Get the full ComfyUI documentation
    docs_content = get_comfyui_docs_content()
    
    # Base system prompt with anycoder-specific instructions
    base_prompt = """You are an expert ComfyUI developer. Generate clean, valid JSON workflows for ComfyUI based on the user's request.

🚨 CRITICAL: READ THE USER'S REQUEST CAREFULLY AND GENERATE A WORKFLOW THAT MATCHES THEIR SPECIFIC NEEDS.

ComfyUI workflows are JSON structures that define:
- Nodes: Individual processing units with specific functions (e.g., CheckpointLoaderSimple, CLIPTextEncode, KSampler, VAEDecode, SaveImage)
- Connections: Links between nodes that define data flow
- Parameters: Configuration values for each node (prompts, steps, cfg, sampler_name, etc.)
- Inputs/Outputs: Data flow between nodes using numbered inputs/outputs

**🚨 YOUR PRIMARY TASK:**
1. **UNDERSTAND what the user is asking for** in their message
2. **CREATE a ComfyUI workflow** that accomplishes their goal
3. **GENERATE ONLY the JSON workflow** - no HTML, no applications, no explanations outside the JSON

**JSON Syntax Rules:**
- Use double quotes for strings
- No trailing commas
- Proper nesting and structure
- Valid data types (string, number, boolean, null, object, array)

**Output Requirements:**
- Generate ONLY the ComfyUI workflow JSON
- The output should be pure, valid JSON that can be loaded directly into ComfyUI
- Do NOT wrap in markdown code fences (no ```json```)
- Do NOT add explanatory text before or after the JSON
- The JSON should be complete and functional

---

## Complete ComfyUI Documentation

Below is the complete, official ComfyUI documentation automatically synced from https://docs.comfy.org/llms.txt:

"""
    
    # Combine base prompt with full documentation
    full_prompt = base_prompt + docs_content
    
    # Add final instructions
    final_instructions = """

---

## Final Instructions

- Always use the exact node types, parameters, and workflow structures from the ComfyUI documentation above
- Pay close attention to the user's specific request and generate a workflow that fulfills it
- Use appropriate nodes for the task (CheckpointLoader, KSampler, VAEDecode, SaveImage, etc.)
- Ensure all node connections are properly defined
- Generate production-ready JSON that can be loaded directly into ComfyUI
- Do NOT generate random or example workflows - create workflows based on the user's actual request
- Always include "Built with anycoder - https://huggingface.co/spaces/akhaliq/anycoder" as a comment in workflow metadata if possible

🚨 REMINDER: Your workflow should directly address what the user asked for. Don't ignore their message!

"""
    
    return full_prompt + final_instructions

def initialize_backend_docs():
    """Initialize backend documentation system on startup"""
    try:
        # Pre-load the Gradio documentation
        gradio_docs = get_gradio_docs_content()
        if gradio_docs:
            print(f"🚀 Gradio documentation initialized ({len(gradio_docs)} chars loaded)")
        else:
            print("⚠️ Gradio documentation initialized with fallback content")
        
        # Pre-load the transformers.js documentation
        transformersjs_docs = get_transformersjs_docs_content()
        if transformersjs_docs:
            print(f"🚀 transformers.js documentation initialized ({len(transformersjs_docs)} chars loaded)")
        else:
            print("⚠️ transformers.js documentation initialized with fallback content")
        
        # Pre-load the ComfyUI documentation
        comfyui_docs = get_comfyui_docs_content()
        if comfyui_docs:
            print(f"🚀 ComfyUI documentation initialized ({len(comfyui_docs)} chars loaded)")
        else:
            print("⚠️ ComfyUI documentation initialized with fallback content")
            
    except Exception as e:
        print(f"Warning: Failed to initialize backend documentation: {e}")

# Initialize on import
if __name__ != "__main__":
    # Only initialize if being imported (not run directly)
    try:
        initialize_backend_docs()
    except Exception as e:
        print(f"Warning: Failed to auto-initialize backend docs: {e}")

