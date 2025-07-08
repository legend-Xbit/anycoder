import os
import re
from http import HTTPStatus
from typing import Dict, List, Optional, Tuple
import base64

import gradio as gr
from huggingface_hub import InferenceClient

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
    }
]

# HF Inference Client
YOUR_API_TOKEN = os.getenv('HF_TOKEN')
client = InferenceClient(
    provider="auto",
    api_key=YOUR_API_TOKEN,
    bill_to="huggingface"
)

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
    return []

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

def generation_code(query: Optional[str], image: Optional[gr.Image], _setting: Dict[str, str], _history: Optional[History], _current_model: Dict):
    if query is None:
        query = ''
    if _history is None:
        _history = []
    messages = history_to_messages(_history, _setting['system'])
    if image is not None:
        messages.append(create_multimodal_message(query, image))
    else:
        messages.append({'role': 'user', 'content': query})
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
                yield {
                    code_output: clean_code,
                    status_indicator: '<div class="status-indicator generating" id="status">Generating code...</div>',
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
        }
    except Exception as e:
        error_message = f"Error: {str(e)}"
        yield {
            code_output: error_message,
            status_indicator: '<div class="status-indicator error" id="status">Error generating code</div>',
        }

# Main application
with gr.Blocks(css_paths="app.css", title="AnyCoder - AI Code Generator") as demo:
    history = gr.State([])
    setting = gr.State({
        "system": SystemPrompt,
    })
    current_model = gr.State(AVAILABLE_MODELS[0])
    current_model_display = gr.Markdown(f"**Model:** {AVAILABLE_MODELS[0]['name']}", elem_classes="model-display")
    open_panel = gr.State(None)

    # Define shared components FIRST so they can be referenced everywhere
    with gr.Row():
        # Sidebar
        with gr.Column(scale=0, min_width=340, elem_classes="sidebar"):
            gr.HTML("""
                <div class="sidebar-header">
                    <img src="https://huggingface.co/spaces/akhaliq/anycoder/resolve/main/Animated_Logo_Video_Ready.gif" width="48px" />
                    <h1>AnyCoder</h1>
                    <div class="sidebar-desc">AI-Powered Code Generator</div>
                </div>
            """)
            input = gr.Textbox(
                label="Describe your application",
                placeholder="e.g., Create a todo app with add, delete, and mark as complete functionality",
                lines=2,
                elem_classes="code-input"
            )
            image_input = gr.Image(
                label="Upload UI design image (ERNIE-4.5-VL only)",
                visible=False,
                elem_classes="image-input"
            )
            with gr.Row():
                btn = gr.Button("Generate", variant="primary", size="sm", elem_classes="generate-btn")
                clear_btn = gr.Button("Clear", variant="secondary", size="sm", elem_classes="clear-btn")
            gr.HTML("""
                <div class="sidebar-section">
                    <h3>How it works</h3>
                    <ul>
                        <li>Describe your app or UI in plain English</li>
                        <li>Optionally upload a UI image (for ERNIE model)</li>
                        <li>Click Generate to get code and preview</li>
                    </ul>
                </div>
            """)
            gr.HTML("<div class='sidebar-section'><h3>Quick Examples</h3></div>")
            for i, demo_item in enumerate(DEMO_LIST[:5]):
                demo_card = gr.Button(
                    value=demo_item['title'], 
                    variant="secondary",
                    size="sm",
                    elem_classes="quick-example-btn sidebar-btn"
                )
                demo_card.click(
                    fn=lambda idx=i: gr.update(value=DEMO_LIST[idx]['description']),
                    outputs=input
                )
            gr.HTML("<hr style='margin: 16px 0;'>")
            with gr.Row():
                modelBtn = gr.Button("🤖 Model", variant="secondary", size="sm", elem_classes="sidebar-btn")
                settingPromptBtn = gr.Button("⚙️ Prompt", variant="secondary", size="sm", elem_classes="sidebar-btn")
                historyBtn = gr.Button("📜 History", variant="secondary", size="sm", elem_classes="sidebar-btn")
            # Place modals/drawers at the end of the sidebar so they overlay the lower part
            with gr.Group(visible=False, elem_classes="modal") as system_prompt_modal:
                gr.HTML("<h3>System Prompt Configuration</h3>")
                systemPromptInput = gr.Textbox(
                    value=SystemPrompt,
                    label="System Prompt",
                    lines=10,
                    elem_classes="modal-input"
                )
                with gr.Row():
                    modal_ok_btn = gr.Button("Save", variant="primary")
                    modal_cancel_btn = gr.Button("Cancel", variant="secondary")

            with gr.Group(visible=False, elem_classes="modal") as model_modal:
                gr.HTML("<h3>Select AI Model</h3>")
                with gr.Row(elem_classes="model-select-row"):
                    for i, model in enumerate(AVAILABLE_MODELS):
                        model_select_btn = gr.Button(
                            value=model['name'],
                            variant="secondary",
                            size="sm",
                            elem_classes="model-card-btn"
                        )
                        model_select_btn.click(
                            lambda m=model: (m, gr.update(visible=False), f"**Model:** {m['name']}", update_image_input_visibility(m)), 
                            outputs=[current_model, model_modal, current_model_display, image_input]
                        )

            with gr.Group(visible=False, elem_classes="drawer") as history_drawer:
                gr.HTML("<h3>Generation History</h3>")
                history_output = gr.Chatbot(show_label=False, height=400, elem_classes="history_chatbot")
        # Main area
        with gr.Column(scale=1, min_width=700, elem_classes="main-area"):
            with gr.Row():
                current_model_display
            with gr.Tabs(elem_classes="code-tabs") as tabs:
                with gr.Tab("Code Editor", elem_classes="code-tab"):
                    code_output = gr.Code(
                        language="html", 
                        lines=25, 
                        interactive=False,
                        elem_classes="code-editor"
                    )
                with gr.Tab("Live Preview", elem_classes="preview-tab"):
                    sandbox = gr.HTML(elem_classes="html_content")
            status_indicator = gr.HTML(
                '<div class="status-indicator" id="status">Ready to generate code</div>',
                elem_classes="status-bar"
            )

    # Event handlers
    settingPromptBtn.click(
        fn=lambda current: toggle_panel(current, "prompt"),
        inputs=[open_panel],
        outputs=[system_prompt_modal, model_modal, history_drawer, open_panel]
    )
    modelBtn.click(
        fn=lambda current: toggle_panel(current, "model"),
        inputs=[open_panel],
        outputs=[system_prompt_modal, model_modal, history_drawer, open_panel]
    )
    historyBtn.click(
        fn=lambda current, history: (*toggle_panel(current, "history")[:3], history, toggle_panel(current, "history")[3]),
        inputs=[open_panel, history],
        outputs=[system_prompt_modal, model_modal, history_drawer, history_output, open_panel]
    )
    modal_ok_btn.click(
        lambda input: ({"system": input}, gr.update(visible=False)), 
        inputs=[systemPromptInput], 
        outputs=[setting, system_prompt_modal]
    )
    modal_cancel_btn.click(lambda: gr.update(visible=False), outputs=[system_prompt_modal])
    btn.click(
        generation_code,
        inputs=[input, image_input, setting, history, current_model],
        outputs=[code_output, history, sandbox, status_indicator]
    )
    clear_btn.click(clear_history, outputs=[history])

def toggle_panel(current, panel):
    # If the requested panel is already open, close all
    if current == panel:
        return (gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), None)
    # Otherwise, open the requested panel and close others
    if panel == "prompt":
        return (gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), "prompt")
    elif panel == "model":
        return (gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), "model")
    elif panel == "history":
        return (gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), "history")
    else:
        return (gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), None)

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=20).launch(ssr_mode=False)