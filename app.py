import os
import re
from http import HTTPStatus
from typing import Dict, List, Optional, Tuple
import base64

import gradio as gr
from huggingface_hub import InferenceClient

import modelscope_studio.components.base as ms
import modelscope_studio.components.legacy as legacy
import modelscope_studio.components.antd as antd

# Configuration
SystemPrompt = """You are a helpful coding assistant. You help users create applications by generating code based on their requirements. 
When asked to create an application, you should:
1. Understand the user's requirements
2. Generate clean, working code
3. Provide HTML output when appropriate for web applications
4. Include necessary comments and documentation
5. Ensure the code is functional and follows best practices

Always respond with code that can be executed or rendered directly.

Always output only the HTML code inside a ```html ... ``` code block, and do not include any explanations or extra text."""

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
    }
]

# HF Inference Client
YOUR_API_TOKEN = os.getenv('HF_TOKEN3')
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
        messages.append({'role': 'user', 'content': h[0]})
        messages.append({'role': 'assistant', 'content': h[1]})
    return messages

def messages_to_history(messages: Messages) -> Tuple[str, History]:
    assert messages[0]['role'] == 'system'
    history = []
    for q, r in zip(messages[1::2], messages[2::2]):
        history.append([q['content'], r['content']])
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
            print("Successfully extracted code block:", extracted)
            return extracted
    # If no code block is found, check if the entire text is HTML
    if text.strip().startswith('<!DOCTYPE html>') or text.strip().startswith('<html'):
        print("Text appears to be raw HTML, using as is")
        return text.strip()
    print("No code block found in text:", text)
    return text.strip()

def history_render(history: History):
    return gr.update(open=True), history

def clear_history():
    return []

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
    print("Generated iframe:", iframe)
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
        print(f"Error in demo_card_click: {e}")
        # Return the first demo description as fallback
        return DEMO_LIST[0]['description']

# Main application
with gr.Blocks(css_paths="app.css") as demo:
    history = gr.State([])
    setting = gr.State({
        "system": SystemPrompt,
    })

    with ms.Application() as app:
        with antd.ConfigProvider():
            with antd.Row(gutter=[32, 12]) as layout:
                with antd.Col(span=24, md=8):
                    with antd.Flex(vertical=True, gap="middle", wrap=True):
                        gr.LoginButton()
                        login_message = gr.Markdown("", visible=False)
                        header = gr.HTML("""
                                  <div class="left_header">
                                   <img src="https://huggingface.co/spaces/akhaliq/anycoder/resolve/main/Animated_Logo_Video_Ready.gif" width="200px" />
                                   <h1>Hugging Face Coder</h1>
                                  </div>
                                   """)
                        input = antd.InputTextarea(
                            size="large", allow_clear=True, placeholder="Please enter what kind of application you want", visible=False)
                        btn = antd.Button("send", type="primary", size="large", visible=False)
                        clear_btn = antd.Button("clear history", type="default", size="large", visible=False)

                        antd.Divider("examples", visible=False)
                        with antd.Flex(gap="small", wrap=True, visible=False) as examples_flex:
                            for i, demo_item in enumerate(DEMO_LIST):
                                with antd.Card(hoverable=True, title=demo_item["title"]) as demoCard:
                                    antd.CardMeta(description=demo_item["description"])
                                demoCard.click(lambda e, idx=i: DEMO_LIST[idx]['description'], outputs=[input])

                        antd.Divider("setting", visible=False)
                        with antd.Flex(gap="small", wrap=True, visible=False) as setting_flex:
                            settingPromptBtn = antd.Button(
                                "⚙️ set system Prompt", type="default", visible=False)
                            codeBtn = antd.Button("🧑‍💻 view code", type="default", visible=False)
                            historyBtn = antd.Button("📜 history", type="default", visible=False)

                    with antd.Modal(open=False, title="set system Prompt", width="800px") as system_prompt_modal:
                        systemPromptInput = antd.InputTextarea(
                            SystemPrompt, auto_size=True)

                    settingPromptBtn.click(lambda: gr.update(
                        open=True), inputs=[], outputs=[system_prompt_modal])
                    system_prompt_modal.ok(lambda input: ({"system": input}, gr.update(
                        open=False)), inputs=[systemPromptInput], outputs=[setting, system_prompt_modal])
                    system_prompt_modal.cancel(lambda: gr.update(
                        open=False), outputs=[system_prompt_modal])

                    with antd.Drawer(open=False, title="code", placement="left", width="750px") as code_drawer:
                        code_output = legacy.Markdown()

                    codeBtn.click(lambda: gr.update(open=True),
                                  inputs=[], outputs=[code_drawer])
                    code_drawer.close(lambda: gr.update(
                        open=False), inputs=[], outputs=[code_drawer])

                    with antd.Drawer(open=False, title="history", placement="left", width="900px") as history_drawer:
                        history_output = legacy.Chatbot(show_label=False, flushing=False, height=960, elem_classes="history_chatbot")

                    historyBtn.click(history_render, inputs=[history], outputs=[history_drawer, history_output])
                    history_drawer.close(lambda: gr.update(
                        open=False), inputs=[], outputs=[history_drawer])

                with antd.Col(span=24, md=16):
                    with ms.Div(elem_classes="right_panel"):
                        gr.HTML('<div class="render_header"><span class="header_btn"></span><span class="header_btn"></span><span class="header_btn"></span></div>')
                        # Move sandbox outside of tabs for always-on visibility
                        sandbox = gr.HTML(elem_classes="html_content")
                        with antd.Tabs(active_key="empty", render_tab_bar="() => null") as state_tab:
                            with antd.Tabs.Item(key="empty"):
                                empty = antd.Empty(description="empty input", elem_classes="right_content")
                            with antd.Tabs.Item(key="loading"):
                                loading = antd.Spin(True, tip="coding...", size="large", elem_classes="right_content")

            def update_login_ui(profile: gr.OAuthProfile | None):
                if profile is None:
                    return (
                        gr.update(value="**You must sign in with Hugging Face to use this app.**", visible=True),
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(visible=False),
                    )
                else:
                    return (
                        gr.update(visible=False),
                        gr.update(visible=True),
                        gr.update(visible=True),
                        gr.update(visible=True),
                        gr.update(visible=True),
                        gr.update(visible=True),
                        gr.update(visible=True),
                        gr.update(visible=True),
                        gr.update(visible=True),
                    )

            def generation_code(query: Optional[str], _setting: Dict[str, str], _history: Optional[History], profile: gr.OAuthProfile | None):
                if profile is None:
                    return (
                        "Please sign in with Hugging Face to use this feature.",
                        _history,
                        None,
                        gr.update(active_key="empty"),
                        gr.update(open=True),
                    )
                if query is None:
                    query = ''
                if _history is None:
                    _history = []
                messages = history_to_messages(_history, _setting['system'])
                messages.append({'role': 'user', 'content': query})

                try:
                    completion = client.chat.completions.create(
                        model="deepseek-ai/DeepSeek-V3-0324",
                        messages=messages,
                        stream=True
                    )
                    
                    content = ""
                    for chunk in completion:
                        if chunk.choices[0].delta.content:
                            content += chunk.choices[0].delta.content
                            yield {
                                code_output: content,
                                state_tab: gr.update(active_key="loading"),
                                code_drawer: gr.update(open=True),
                            }
                    
                    # Final response
                    _history = messages_to_history(messages + [{
                        'role': 'assistant',
                        'content': content
                    }])
                    
                    yield {
                        code_output: content,
                        history: _history,
                        sandbox: send_to_sandbox(remove_code_block(content)),
                        state_tab: gr.update(active_key="render"),
                        code_drawer: gr.update(open=False),
                    }
                    
                except Exception as e:
                    error_message = f"Error: {str(e)}"
                    yield {
                        code_output: error_message,
                        state_tab: gr.update(active_key="empty"),
                        code_drawer: gr.update(open=True),
                    }

            btn.click(
                generation_code,
                inputs=[input, setting, history],
                outputs=[code_output, history, sandbox, state_tab, code_drawer]
            )
            
            clear_btn.click(clear_history, inputs=[], outputs=[history])

            demo.load(
                update_login_ui,
                inputs=None,
                outputs=[
                    login_message,
                    input,
                    btn,
                    clear_btn,
                    examples_flex,
                    setting_flex,
                    settingPromptBtn,
                    codeBtn,
                    historyBtn,
                ]
            )

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=20).launch(ssr_mode=False)