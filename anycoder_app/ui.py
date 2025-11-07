"""
Gradio user interface for AnyCoder.
Defines the main UI layout, components, and event handlers.
"""
import os
import gradio as gr
from typing import Dict, Optional
from huggingface_hub import HfApi

from .config import (
    AVAILABLE_MODELS, DEFAULT_MODEL, DEFAULT_MODEL_NAME,
    LANGUAGE_CHOICES, get_gradio_language
)
from .themes import THEME_CONFIGS, get_saved_theme, current_theme
from .prompts import HTML_SYSTEM_PROMPT
from .models import history_to_chatbot_messages
from .parsers import (
    history_render, clear_history, create_multimodal_message,
    parse_multipage_html_output, parse_transformers_js_output,
    parse_react_output, format_transformers_js_output,
    validate_and_autofix_files, parse_multi_file_python_output,
    is_streamlit_code, is_gradio_code
)
from .deploy import (
    check_authentication, update_ui_for_auth_status,
    generation_code, deploy_to_spaces, add_anycoder_tag_to_readme,
    _parse_repo_or_model_url, load_project_from_url, check_hf_space_url,
    import_repo_to_app, extract_import_statements, 
    generate_requirements_txt_with_llm, prettify_comfyui_json_for_html
)

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
        /* App link styling (visible on all devices) */
        .app-link {
            display: block;
            padding: 12px;
            border-radius: 8px;
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.3);
            margin: 12px 0;
            text-align: center;
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
        
        # App link (visible on all devices)
        mobile_link = gr.Markdown(
            """
            <div class="app-link">
                📱 <strong>Using Mobile?</strong><br/>
                <a href="https://akhaliq-anycoder.hf.space" target="_blank" style="color: #007bff; text-decoration: underline;">
                    Use the app here
                </a>
            </div>
            """,
            visible=True
        )


        # Unified Import section
        import_header_md = gr.Markdown("📥 Import Project (Space, GitHub, or Model)", visible=False)
        load_project_url = gr.Textbox(
            label="Project URL",
            placeholder="https://huggingface.co/spaces/user/space OR https://huggingface.co/user/model OR https://github.com/owner/repo",
            lines=1
        , visible=False)
        load_project_btn = gr.Button("📥 Import Project", variant="secondary", size="sm", visible=True)
        load_project_status = gr.Markdown(visible=False)
        
        # Chat history display in sidebar
        chat_history = gr.Chatbot(
            label="Conversation History",
            type="messages",
            height=300,
            show_copy_button=True,
            visible=True
        )
        
        # Input textbox for new messages
        input = gr.Textbox(
            label="What would you like to build?",
            placeholder="🔒 Please log in with Hugging Face to use AnyCoder...",
            lines=2,
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
                gr.update(),  # language dropdown - no change
                []  # chat_history
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
                gr.update(value=framework_type),  # set language dropdown to framework type
                history_to_chatbot_messages(loaded_history)  # chat_history
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
                gr.update(value=framework_type),  # set language dropdown to detected language
                history_to_chatbot_messages(loaded_history)  # chat_history
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
            chat_history,  # Add chat_history to outputs
        ],
    )





    def begin_generation_ui():
        # Collapse the sidebar when generation starts; keep status hidden
        return [gr.update(open=False), gr.update(visible=False)]

    def end_generation_ui():
        # Open sidebar after generation; hide the status
        return [gr.update(open=True), gr.update(visible=False)]

    def generation_code_wrapper(inp, sett, hist, model, lang, prov, profile: Optional[gr.OAuthProfile] = None, token: Optional[gr.OAuthToken] = None):
        """Wrapper to call generation_code and pass component references"""
        # Generate code and update both history and chat_history
        for result in generation_code(inp, sett, hist, model, lang, prov, profile, token, code_output, history_output, history):
            # generation_code yields dictionaries with component keys
            # Extract the values and yield them for our outputs
            code_val = result.get(code_output, "")
            hist_val = result.get(history, hist)
            history_output_val = result.get(history_output, [])
            # Yield for: code_output, history, history_output, chat_history
            yield code_val, hist_val, history_output_val, history_output_val

    btn.click(
        begin_generation_ui,
        inputs=None,
        outputs=[sidebar, generating_status],
        show_progress="hidden",
    ).then(
        generation_code_wrapper,
        inputs=[input, setting, history, current_model, language_dropdown, provider_state],
        outputs=[code_output, history, history_output, chat_history]
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
        outputs=[code_output, history, history_output, chat_history]
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

    def _extract_url(text: str) -> Optional[str]:
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
    
    clear_btn.click(clear_history, outputs=[history, history_output, chat_history])
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
        profile: Optional[gr.OAuthProfile] = None, 
        token: Optional[gr.OAuthToken] = None
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
        profile: Optional[gr.OAuthProfile] = None, 
        token: Optional[gr.OAuthToken] = None
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
                    
                    # If Dockerfile is missing, use template
                    if 'Dockerfile' not in files:
                        files['Dockerfile'] = """FROM node:18-slim

# Use the existing node user (UID 1000)
USER node

# Set environment variables
ENV HOME=/home/node \\
    PATH=/home/node/.local/bin:$PATH

# Set working directory
WORKDIR /home/node/app

# Copy package files with proper ownership
COPY --chown=node:node package*.json ./

# Install dependencies
RUN npm install

# Copy rest of the application with proper ownership
COPY --chown=node:node . .

# Build the Next.js app
RUN npm run build

# Expose port 7860
EXPOSE 7860

# Start the application on port 7860
CMD ["npm", "start", "--", "-p", "7860"]
"""
                    
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
                                # Determine file extension
                                if file_name == 'Dockerfile':
                                    suffix = ''
                                else:
                                    suffix = f".{file_name.split('.')[-1]}"
                                
                                with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False) as f:
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
                
                # Streamlit logic - Parse multi-file structure
                files = parse_multi_file_python_output(code)
                if not files:
                    return gr.update(value="Error: Could not parse Streamlit output. Please regenerate the code.", visible=True)
                
                # Verify required files exist
                has_streamlit_app = 'streamlit_app.py' in files or 'app.py' in files
                has_requirements = 'requirements.txt' in files
                has_dockerfile = 'Dockerfile' in files
                
                if not has_streamlit_app:
                    return gr.update(value="Error: Missing streamlit_app.py. Please regenerate the code.", visible=True)
                
                # If Dockerfile or requirements.txt is missing, generate them
                if not has_dockerfile:
                    # Generate default Dockerfile
                    files['Dockerfile'] = """FROM python:3.11-slim

# Set up user with ID 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \\
    PATH=/home/user/.local/bin:$PATH

# Set working directory
WORKDIR $HOME/app

# Copy requirements file with proper ownership
COPY --chown=user requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files with proper ownership
COPY --chown=user . .

# Expose port 7860
EXPOSE 7860

# Start Streamlit app
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=7860", "--server.address=0.0.0.0"]
"""
                
                if not has_requirements:
                    # Generate requirements.txt from imports in the main app file
                    main_app = files.get('streamlit_app.py') or files.get('app.py', '')
                    import_statements = extract_import_statements(main_app)
                    files['requirements.txt'] = generate_requirements_txt_with_llm(import_statements)
                
                # Upload Streamlit files
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
                            # Determine file extension
                            if file_name == 'Dockerfile':
                                suffix = ''
                            else:
                                suffix = f".{file_name.split('.')[-1]}"
                            
                            with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False) as f:
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
                return gr.update(value=f"✅ {action_text}! [Open your Streamlit Space here]({space_url})", visible=True)
                    
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
            parse_error = None
            try:
                files = parse_multipage_html_output(code)
                print(f"[Deploy] Parsed files: {list(files.keys())}")
                files = validate_and_autofix_files(files)
                print(f"[Deploy] After validation: {list(files.keys())}")
            except Exception as e:
                parse_error = str(e)
                print(f"[Deploy] Parse error: {parse_error}")
                files = {}
            
            # If we have multiple files (or at least a parsed index.html), upload the whole folder
            if isinstance(files, dict) and len(files) > 0 and files.get('index.html'):
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
    ).then(
        lambda hist: history_to_chatbot_messages(hist),
        inputs=[history],
        outputs=[chat_history]
    )
    # Keep the old deploy method as fallback (if not logged in, user can still use the old method)
    # Optionally, you can keep the old deploy_btn.click for the default method as a secondary button.
    
    # Handle authentication state updates
    # The LoginButton automatically handles OAuth flow and passes profile/token to the function
    def handle_auth_update(profile: Optional[gr.OAuthProfile] = None, token: Optional[gr.OAuthToken] = None):
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

