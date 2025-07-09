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

import gradio as gr
from huggingface_hub import InferenceClient
from tavily import TavilyClient

# Configuration
SystemPrompt = """You are a helpful coding assistant. You help users create applications by generating code based on their requirements. 
When asked to create an application, you should:
1. Understand the user's requirements
2. Generate clean, working code
3. Provide HTML output when appropriate for web applications
4. Include necessary comments and documentation
5. Ensure the code is functional and follows best practices

If an image is provided, analyze it and use the visual information to better understand the user's requirements.

Always respond with code that can be executed or rendered directly.

Always output only the HTML code inside a ```html ... ``` code block, and do not include any explanations or extra text."""

# System prompt with search capability
SystemPromptWithSearch = """You are a helpful coding assistant with access to real-time web search. You help users create applications by generating code based on their requirements. 
When asked to create an application, you should:
1. Understand the user's requirements
2. Use web search when needed to find the latest information, best practices, or specific technologies
3. Generate clean, working code
4. Provide HTML output when appropriate for web applications
5. Include necessary comments and documentation
6. Ensure the code is functional and follows best practices

If an image is provided, analyze it and use the visual information to better understand the user's requirements.

Always respond with code that can be executed or rendered directly.

Always output only the HTML code inside a ```html ... ``` code block, and do not include any explanations or extra text."""

# Available models
AVAILABLE_MODELS = [
    {
        "name": "DeepSeek V3",
        "id": "deepseek-ai/DeepSeek-V3-0324",
        "description": "DeepSeek V3 model for code generation"
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
    }
]

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
        "title": "Weather Dashboard",
        "description": "Create a weather dashboard that displays current weather information"
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
    }
]

# HF Inference Client
YOUR_API_TOKEN = os.getenv('HF_TOKEN')
client = InferenceClient(
    provider="auto",
    api_key=YOUR_API_TOKEN,
    bill_to="huggingface"
)

# Tavily Search Client
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')
tavily_client = None
if TAVILY_API_KEY:
    try:
        tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
    except Exception as e:
        print(f"Failed to initialize Tavily client: {e}")
        tavily_client = None

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
            return extracted
    # If no code block is found, check if the entire text is HTML
    if text.strip().startswith('<!DOCTYPE html>') or text.strip().startswith('<html') or text.strip().startswith('<'):
        return text.strip()
    return text.strip()

def history_render(history: History):
    return gr.update(visible=True), history

def clear_history():
    return [], []  # Empty lists for both tuple format and chatbot messages

def update_image_input_visibility(model):
    """Update image input visibility based on selected model"""
    is_ernie_vl = model.get("id") == "baidu/ERNIE-4.5-VL-424B-A47B-Base-PT"
    return gr.update(visible=is_ernie_vl)

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
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"

def create_multimodal_message(text, image=None):
    """Create a multimodal message with text and optional image"""
    if image is None:
        return {"role": "user", "content": text}
    
    content = [
        {
            "type": "text",
            "text": text
        },
        {
            "type": "image_url",
            "image_url": {
                "url": process_image_for_model(image)
            }
        }
    ]
    
    return {"role": "user", "content": content}

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
    # Add a wrapper to inject necessary permissions and ensure full HTML
    wrapped_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset=\"UTF-8\">
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
        <script>
            // Safe localStorage polyfill
            const safeStorage = {{
                _data: {{}},
                getItem: function(key) {{ return this._data[key] || null; }},
                setItem: function(key, value) {{ this._data[key] = value; }},
                removeItem: function(key) {{ delete this._data[key]; }},
                clear: function() {{ this._data = {{}}; }}
            }};
            Object.defineProperty(window, 'localStorage', {{
                value: safeStorage,
                writable: false
            }});
            window.onerror = function(message, source, lineno, colno, error) {{
                console.error('Error:', message);
            }};
        </script>
    </head>
    <body>
        {code}
    </body>
    </html>
    """
    encoded_html = base64.b64encode(wrapped_code.encode('utf-8')).decode('utf-8')
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

def generation_code(query: Optional[str], image: Optional[gr.Image], file: Optional[str], _setting: Dict[str, str], _history: Optional[History], _current_model: Dict, enable_search: bool = False):
    if query is None:
        query = ''
    if _history is None:
        _history = []
    
    # Choose system prompt based on search setting
    system_prompt = SystemPromptWithSearch if enable_search else _setting['system']
    messages = history_to_messages(_history, system_prompt)
    
    # Extract file text and append to query if file is present
    file_text = ""
    if file:
        file_text = extract_text_from_file(file)
        if file_text:
            file_text = file_text[:5000]  # Limit to 5000 chars for prompt size
            query = f"{query}\n\n[Reference file content below]\n{file_text}"
    
    # Enhance query with search if enabled
    enhanced_query = enhance_query_with_search(query, enable_search)
    
    if image is not None:
        messages.append(create_multimodal_message(enhanced_query, image))
    else:
        messages.append({'role': 'user', 'content': enhanced_query})
    try:
        completion = client.chat.completions.create(
            model=_current_model["id"],
            messages=messages,
            stream=True,
            max_tokens=5000
        )
        content = ""
        for chunk in completion:
            if chunk.choices[0].delta.content:
                content += chunk.choices[0].delta.content
                clean_code = remove_code_block(content)
                search_status = " (with web search)" if enable_search and tavily_client else ""
                yield {
                    code_output: clean_code,
                    status_indicator: f'<div class="status-indicator generating" id="status">Generating code{search_status}...</div>',
                    history_output: history_to_chatbot_messages(_history),
                }
        _history = messages_to_history(messages + [{
            'role': 'assistant',
            'content': content
        }])
        yield {
            code_output: remove_code_block(content),
            history: _history,
            sandbox: send_to_sandbox(remove_code_block(content)),
            status_indicator: '<div class="status-indicator success" id="status">Code generated successfully!</div>',
            history_output: history_to_chatbot_messages(_history),
        }
    except Exception as e:
        error_message = f"Error: {str(e)}"
        yield {
            code_output: error_message,
            status_indicator: '<div class="status-indicator error" id="status">Error generating code</div>',
            history_output: history_to_chatbot_messages(_history),
        }

# Main application
with gr.Blocks(theme=gr.themes.Base(), title="AnyCoder - AI Code Generator") as demo:
    history = gr.State([])
    setting = gr.State({
        "system": SystemPrompt,
    })
    current_model = gr.State(AVAILABLE_MODELS[0])
    open_panel = gr.State(None)

    with gr.Sidebar():
        gr.Markdown("# AnyCoder\nAI-Powered Code Generator")
        gr.Markdown("""Describe your app or UI in plain English. Optionally upload a UI image (for ERNIE model). Click Generate to get code and preview.""")
        gr.Markdown("**Tip:** For best search results about people or entities, include details like profession, company, or location. Example: 'John Smith software engineer at Google.'")
        gr.Markdown("**Tip:** You can attach a file (PDF, TXT, DOCX, CSV, MD, Images) to use as reference for your prompt, e.g. 'Summarize this PDF' or 'Extract text from this image'.")
        input = gr.Textbox(
            label="Describe your application",
            placeholder="e.g., Create a todo app with add, delete, and mark as complete functionality",
            lines=2
        )
        image_input = gr.Image(
            label="Upload UI design image (ERNIE-4.5-VL only)",
            visible=False
        )
        file_input = gr.File(
            label="Attach a file (PDF, TXT, DOCX, CSV, MD, Images)",
            file_types=[".pdf", ".txt", ".md", ".csv", ".docx", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".gif", ".webp"],
            visible=True
        )
        with gr.Row():
            btn = gr.Button("Generate", variant="primary", size="sm")
            clear_btn = gr.Button("Clear", variant="secondary", size="sm")
        
        # Search toggle
        search_toggle = gr.Checkbox(
            label="🔍 Enable Web Search",
            value=False,
            info="Enable real-time web search to get the latest information and best practices"
        )
        
        # Search status indicator
        if not tavily_client:
            gr.Markdown("⚠️ **Web Search Unavailable**: Set `TAVILY_API_KEY` environment variable to enable search")
        else:
            gr.Markdown("✅ **Web Search Available**: Toggle above to enable real-time search")
        
        gr.Markdown("📷 **Image Text Extraction**: Upload images to extract text using OCR (requires Tesseract installation)")
        
        gr.Markdown("### Quick Examples")
        for i, demo_item in enumerate(DEMO_LIST[:5]):
            demo_card = gr.Button(
                value=demo_item['title'], 
                variant="secondary",
                size="sm"
            )
            demo_card.click(
                fn=lambda idx=i: gr.update(value=DEMO_LIST[idx]['description']),
                outputs=input
            )
        gr.Markdown("---")
        model_dropdown = gr.Dropdown(
            choices=[model['name'] for model in AVAILABLE_MODELS],
            value=AVAILABLE_MODELS[0]['name'],
            label="Select Model"
        )
        def on_model_change(model_name):
            for m in AVAILABLE_MODELS:
                if m['name'] == model_name:
                    return m, f"**Model:** {m['name']}", update_image_input_visibility(m)
            return AVAILABLE_MODELS[0], f"**Model:** {AVAILABLE_MODELS[0]['name']}", update_image_input_visibility(AVAILABLE_MODELS[0])
        model_display = gr.Markdown(f"**Model:** {AVAILABLE_MODELS[0]['name']}")
        model_dropdown.change(
            on_model_change,
            inputs=model_dropdown,
            outputs=[current_model, model_display, image_input]
        )
        with gr.Accordion("System Prompt", open=False):
            systemPromptInput = gr.Textbox(
                value=SystemPrompt,
                label="System Prompt",
                lines=10
            )
            save_prompt_btn = gr.Button("Save", variant="primary")
            def save_prompt(input):
                return {setting: {"system": input}}
            save_prompt_btn.click(save_prompt, inputs=systemPromptInput, outputs=setting)

    with gr.Column():
        model_display
        with gr.Tabs():
            with gr.Tab("Code Editor"):
                code_output = gr.Code(
                    language="html", 
                    lines=25, 
                    interactive=False,
                    label="Generated Code"
                )
            with gr.Tab("Live Preview"):
                sandbox = gr.HTML(label="Live Preview")
            with gr.Tab("History"):
                history_output = gr.Chatbot(show_label=False, height=400, type="messages")
        status_indicator = gr.Markdown(
            'Ready to generate code',
        )

    # Event handlers
    btn.click(
        generation_code,
        inputs=[input, image_input, file_input, setting, history, current_model, search_toggle],
        outputs=[code_output, history, sandbox, status_indicator, history_output]
    )
    clear_btn.click(clear_history, outputs=[history, history_output, file_input])

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=20).launch(ssr_mode=True, mcp_server=True)