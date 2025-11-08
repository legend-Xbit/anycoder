"""
Deployment utilities for publishing to HuggingFace Spaces.
Handles authentication, space creation, and code deployment.
"""
import os
import re
import json
import uuid
import tempfile
import shutil
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import html2text

import gradio as gr
from huggingface_hub import HfApi, InferenceClient
from openai import OpenAI

from .config import HF_TOKEN, get_gradio_language
from .parsers import (
    parse_transformers_js_output, parse_multipage_html_output,
    parse_multi_file_python_output, parse_react_output,
    remove_code_block, is_streamlit_code, is_gradio_code,
    clean_requirements_txt_content, History,
    format_transformers_js_output, build_transformers_inline_html,
    send_transformers_to_sandbox, validate_and_autofix_files,
    inline_multipage_into_single_preview, apply_search_replace_changes,
    apply_transformers_js_search_replace_changes, send_to_sandbox,
    format_multi_file_python_output, send_streamlit_to_stlite,
    send_gradio_to_lite, extract_html_document
)
from .models import (
    get_inference_client, get_real_model_id, history_to_messages, 
    history_to_chatbot_messages, strip_placeholder_thinking,
    is_placeholder_thinking_only, extract_last_thinking_line,
    strip_thinking_tags
)
from . import prompts
from .prompts import (
    HTML_SYSTEM_PROMPT,
    TRANSFORMERS_JS_SYSTEM_PROMPT, STREAMLIT_SYSTEM_PROMPT,
    REACT_SYSTEM_PROMPT, REACT_FOLLOW_UP_SYSTEM_PROMPT,
    JSON_SYSTEM_PROMPT,
    GENERIC_SYSTEM_PROMPT, MULTIPAGE_HTML_SYSTEM_PROMPT,
    DYNAMIC_MULTIPAGE_HTML_SYSTEM_PROMPT,
    FollowUpSystemPrompt, GradioFollowUpSystemPrompt,
    TransformersJSFollowUpSystemPrompt
)
from .docs_manager import get_comfyui_system_prompt, update_gradio_system_prompts, update_json_system_prompts


def check_authentication(profile: Optional[gr.OAuthProfile] = None, token: Optional[gr.OAuthToken] = None) -> Tuple[bool, str]:
    """Check if user is authenticated and return status with message."""
    if not profile or not token:
        return False, "Please log in with your Hugging Face account to use AnyCoder."
    
    if not token.token:
        return False, "Authentication token is invalid. Please log in again."
    
    return True, f"Authenticated as {profile.username}"


def update_ui_for_auth_status(profile: Optional[gr.OAuthProfile] = None, token: Optional[gr.OAuthToken] = None):
    """Update UI components based on authentication status."""
    is_authenticated, auth_message = check_authentication(profile, token)
    
    if is_authenticated:
        # User is authenticated - enable all components
        return (
            gr.update(interactive=True, placeholder="Describe your application..."),  # input
            gr.update(interactive=True, variant="primary")  # btn
        )
    else:
        # User not authenticated - disable main components
        return (
            gr.update(
                interactive=False, 
                placeholder="🔒 Click Sign in with Hugging Face button to use AnyCoder for free"
            ),  # input
            gr.update(interactive=False, variant="secondary")  # btn
        )


def generation_code(query: Optional[str], _setting: Dict[str, str], _history: Optional[History], _current_model: Dict, language: str = "html", provider: str = "auto", profile: Optional[gr.OAuthProfile] = None, token: Optional[gr.OAuthToken] = None, code_output=None, history_output=None, history=None):
    # Check authentication first
    is_authenticated, auth_message = check_authentication(profile, token)
    if not is_authenticated:
        error_message = f"🔒 Authentication Required\n\n{auth_message}\n\nPlease click the 'Sign in with Hugging Face' button in the sidebar to continue."
        if code_output is not None and history_output is not None:
            yield {
                code_output: error_message,
                history_output: history_to_chatbot_messages(_history or []),
            }
        else:
            yield (error_message, _history or [], history_to_chatbot_messages(_history or []))
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
        
        # Check if this is imported model code (should NOT be treated as existing content to modify)
        is_imported_model_code = (
            "Imported model:" in _history[-1][0] or 
            "Imported inference provider code" in last_assistant_msg or
            "Imported transformers/diffusers code" in last_assistant_msg or
            "Switched code type" in _history[-1][0]
        )
        
        # Only treat as existing content if it's NOT imported model code
        if not is_imported_model_code:
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

    # Update system prompts if needed
    if language == "gradio":
        update_gradio_system_prompts()
        print(f"[Generation] Updated Gradio system prompt (length: {len(prompts.GRADIO_SYSTEM_PROMPT)} chars)")
    elif language == "json":
        update_json_system_prompts()
        print(f"[Generation] Updated JSON system prompt (length: {len(prompts.JSON_SYSTEM_PROMPT)} chars)")

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
            # Access GRADIO_SYSTEM_PROMPT from prompts module to get updated value
            system_prompt = prompts.GRADIO_SYSTEM_PROMPT
        elif language == "streamlit":
            system_prompt = STREAMLIT_SYSTEM_PROMPT
        elif language == "json":
            # Access JSON_SYSTEM_PROMPT from prompts module to get updated value
            system_prompt = prompts.JSON_SYSTEM_PROMPT
        elif language == "comfyui":
            system_prompt = get_comfyui_system_prompt()
        else:
            system_prompt = GENERIC_SYSTEM_PROMPT.format(language=language)
    
    # Debug: Log system prompt info
    prompt_preview = system_prompt[:200] if system_prompt else "None"
    print(f"[Generation] Using system prompt (first 200 chars): {prompt_preview}...")
    print(f"[Generation] System prompt total length: {len(system_prompt) if system_prompt else 0} chars")

    messages = history_to_messages(_history, system_prompt)

    # Use the original query without any enhancements - let the system prompt handle everything
    enhanced_query = query

    # Check if this is GLM-4.5 model and handle with simple HuggingFace InferenceClient
    if _current_model["id"] == "zai-org/GLM-4.5":
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
    
    # Use dynamic client based on selected model
    client = get_inference_client(_current_model["id"], provider)
    
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
                
                # Strip thinking tags and tool call markers from all streaming chunks
                chunk_content = strip_thinking_tags(chunk_content)
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

def check_hf_space_url(url: str) -> Tuple[bool, Optional[str], Optional[str]]:
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

def get_trending_models(limit: int = 10) -> List[Tuple[str, str]]:
    """
    Fetch top trending models from HuggingFace Hub.
    
    Returns a list of tuples: (display_name, model_id)
    Display name format: "model_name (task)"
    """
    try:
        # Use the HuggingFace trending API endpoint directly
        response = requests.get("https://huggingface.co/api/trending")
        
        if response.status_code != 200:
            print(f"Failed to fetch trending models: HTTP {response.status_code}")
            return [("Unable to load trending models", "")]
        
        trending_data = response.json()
        
        # The API returns {"recentlyTrending": [...]}
        recently_trending = trending_data.get("recentlyTrending", [])
        
        if not recently_trending:
            print("No trending items found in API response")
            return [("No trending models available", "")]
        
        trending_list = []
        count = 0
        
        # Process trending items, filter for models only
        for item in recently_trending:
            if count >= limit:
                break
            
            try:
                # Check if this is a model (not a space or dataset)
                repo_type = item.get("repoType")
                if repo_type != "model":
                    continue
                
                # Extract model data
                repo_data = item.get("repoData", {})
                model_id = repo_data.get("id")
                
                if not model_id:
                    continue
                
                # Get pipeline tag (task type)
                pipeline_tag = repo_data.get("pipeline_tag")
                
                # Default to "general" if no task found
                task = pipeline_tag or "general"
                
                # Clean up task name for display
                task_display = task.replace("-", " ").title() if task != "general" else "General"
                
                # Create display name: "model_name (Task)"
                display_name = f"{model_id} ({task_display})"
                trending_list.append((display_name, model_id))
                count += 1
                
            except Exception as model_error:
                print(f"Error processing trending item: {model_error}")
                continue
        
        if not trending_list:
            print("No models found in trending list, using fallback")
            # Fallback: use list_models with downloads sort
            try:
                api = HfApi()
                models = api.list_models(sort="downloads", limit=limit)
                for model in models:
                    model_id = model.id
                    task = getattr(model, "pipeline_tag", None) or "general"
                    task_display = task.replace("-", " ").title() if task != "general" else "General"
                    display_name = f"{model_id} ({task_display})"
                    trending_list.append((display_name, model_id))
            except Exception as fallback_error:
                print(f"Fallback also failed: {fallback_error}")
                return [("No models available", "")]
        
        return trending_list
        
    except Exception as e:
        print(f"Error fetching trending models: {e}")
        # Fallback to most downloaded models
        try:
            api = HfApi()
            models = api.list_models(sort="downloads", limit=limit)
            trending_list = []
            for model in models:
                model_id = model.id
                task = getattr(model, "pipeline_tag", None) or "general"
                task_display = task.replace("-", " ").title() if task != "general" else "General"
                display_name = f"{model_id} ({task_display})"
                trending_list.append((display_name, model_id))
            return trending_list
        except Exception:
            return [("Error loading models", "")]


def get_trending_spaces(limit: int = 10) -> List[Tuple[str, str]]:
    """
    Fetch top trending spaces from HuggingFace Hub.
    
    Returns a list of tuples: (display_name, space_id)
    Display name format: "space_name (category)"
    """
    try:
        # Use the HuggingFace trending API endpoint for spaces
        response = requests.get("https://huggingface.co/api/trending?type=space")
        
        if response.status_code != 200:
            print(f"Failed to fetch trending spaces: HTTP {response.status_code}")
            return [("Unable to load trending spaces", "")]
        
        trending_data = response.json()
        
        # The API returns {"recentlyTrending": [...]}
        recently_trending = trending_data.get("recentlyTrending", [])
        
        if not recently_trending:
            print("No trending spaces found in API response")
            return [("No trending spaces available", "")]
        
        trending_list = []
        count = 0
        
        # Process trending items
        for item in recently_trending:
            if count >= limit:
                break
            
            try:
                # Check if this is a space
                repo_type = item.get("repoType")
                if repo_type != "space":
                    continue
                
                # Extract space data
                repo_data = item.get("repoData", {})
                space_id = repo_data.get("id")
                
                if not space_id:
                    continue
                
                # Get title and category
                title = repo_data.get("title") or space_id
                category = repo_data.get("ai_category") or repo_data.get("shortDescription", "Space")
                
                # Create display name: "title (category)"
                # Truncate long titles
                if len(title) > 40:
                    title = title[:37] + "..."
                
                display_name = f"{title} ({category})"
                trending_list.append((display_name, space_id))
                count += 1
                
            except Exception as space_error:
                print(f"Error processing trending space: {space_error}")
                continue
        
        if not trending_list:
            return [("No spaces available", "")]
        
        return trending_list
        
    except Exception as e:
        print(f"Error fetching trending spaces: {e}")
        return [("Error loading spaces", "")]


def import_space_from_hf(space_id: str) -> Tuple[str, str, str, str]:
    """
    Import a HuggingFace space by ID and extract its code.
    
    Returns: (status, code, language, space_url)
    """
    if not space_id or space_id == "":
        return "Please select a space.", "", "html", ""
    
    # Build space URL
    space_url = f"https://huggingface.co/spaces/{space_id}"
    
    # Use existing load_project_from_url function
    status, code = load_project_from_url(space_url)
    
    # Determine language based on code content
    code_lang = "html"  # default
    language = "html"  # for language dropdown
    
    # Check imports to determine framework for Python code
    if is_streamlit_code(code):
        code_lang = "python"
        language = "streamlit"
    elif is_gradio_code(code):
        code_lang = "python"
        language = "gradio"
    elif "=== index.html ===" in code and "=== index.js ===" in code:
        code_lang = "html"
        language = "transformers.js"
    elif ("import " in code or "def " in code) and not ("<!DOCTYPE html>" in code or "<html" in code):
        code_lang = "python"
        language = "gradio"  # Default to Gradio for Python spaces
    
    return status, code, language, space_url


def _generate_inference_code_template(model_id: str, pipeline_tag: Optional[str], has_inference_providers: bool) -> Optional[str]:
    """
    Generate inference provider code template based on model's pipeline tag.
    
    Args:
        model_id: The HuggingFace model ID
        pipeline_tag: The model's pipeline tag (e.g., "text-generation", "text-to-image")
        has_inference_providers: Whether the model has inference providers available
    
    Returns:
        Generated code snippet or None
    """
    if not has_inference_providers:
        return None
    
    # Map pipeline tags to code templates based on HuggingFace Inference Providers docs
    # https://huggingface.co/docs/inference-providers
    
    # Chat Completion / Text Generation models
    if pipeline_tag in ["text-generation", "conversational"]:
        return f'''import os
from huggingface_hub import InferenceClient

client = InferenceClient(
    api_key=os.environ["HF_TOKEN"],
)

completion = client.chat.completions.create(
    model="{model_id}",
    messages=[
        {{
            "role": "user",
            "content": "What is the capital of France?"
        }}
    ],
)

print(completion.choices[0].message)'''
    
    # Vision-Language Models (Image-Text to Text)
    elif pipeline_tag in ["image-text-to-text", "visual-question-answering"]:
        return f'''import os
from huggingface_hub import InferenceClient

client = InferenceClient(
    api_key=os.environ["HF_TOKEN"],
)

completion = client.chat.completions.create(
    model="{model_id}",
    messages=[
        {{
            "role": "user",
            "content": [
                {{
                    "type": "text",
                    "text": "Describe this image in one sentence."
                }},
                {{
                    "type": "image_url",
                    "image_url": {{
                        "url": "https://cdn.britannica.com/61/93061-050-99147DCE/Statue-of-Liberty-Island-New-York-Bay.jpg"
                    }}
                }}
            ]
        }}
    ],
)

print(completion.choices[0].message)'''
    
    # Text to Image models
    elif pipeline_tag == "text-to-image":
        return f'''import os
from huggingface_hub import InferenceClient

client = InferenceClient(
    api_key=os.environ["HF_TOKEN"],
)

# output is a PIL.Image object
image = client.text_to_image(
    "Astronaut riding a horse",
    model="{model_id}",
)

# Save the image
image.save("output.png")'''
    
    # Text to Video models
    elif pipeline_tag == "text-to-video":
        return f'''import os
from huggingface_hub import InferenceClient

client = InferenceClient(
    api_key=os.environ["HF_TOKEN"],
)

video = client.text_to_video(
    "A young man walking on the street",
    model="{model_id}",
)

# Save the video
with open("output.mp4", "wb") as f:
    f.write(video)'''
    
    # Image to Image models
    elif pipeline_tag == "image-to-image":
        return f'''import os
from huggingface_hub import InferenceClient
from PIL import Image

client = InferenceClient(
    api_key=os.environ["HF_TOKEN"],
)

# Load input image
input_image = Image.open("input.jpg")

# output is a PIL.Image object
output_image = client.image_to_image(
    input_image,
    model="{model_id}",
    prompt="Make it more vibrant"
)

# Save the output
output_image.save("output.png")'''
    
    # Text to Speech models
    elif pipeline_tag == "text-to-speech":
        return f'''import os
from huggingface_hub import InferenceClient

client = InferenceClient(
    api_key=os.environ["HF_TOKEN"],
)

audio = client.text_to_speech(
    "Hello world",
    model="{model_id}",
)

# Save the audio
with open("output.mp3", "wb") as f:
    f.write(audio)'''
    
    # Automatic Speech Recognition
    elif pipeline_tag == "automatic-speech-recognition":
        return f'''import os
from huggingface_hub import InferenceClient

client = InferenceClient(
    api_key=os.environ["HF_TOKEN"],
)

with open("audio.mp3", "rb") as f:
    audio_data = f.read()

result = client.automatic_speech_recognition(
    audio_data,
    model="{model_id}",
)

print(result)'''
    
    # Feature Extraction / Embeddings
    elif pipeline_tag == "feature-extraction":
        return f'''import os
from huggingface_hub import InferenceClient

client = InferenceClient(
    api_key=os.environ["HF_TOKEN"],
)

embeddings = client.feature_extraction(
    "Hello world",
    model="{model_id}",
)

print(embeddings)'''
    
    # Default: try chat completion for conversational models
    else:
        # If it has inference providers but unknown task, try chat completion
        return f'''import os
from huggingface_hub import InferenceClient

client = InferenceClient(
    api_key=os.environ["HF_TOKEN"],
)

completion = client.chat.completions.create(
    model="{model_id}",
    messages=[
        {{
            "role": "user",
            "content": "Hello, how are you?"
        }}
    ],
)

print(completion.choices[0].message)'''


def _fetch_inference_provider_code(model_id: str) -> Optional[str]:
    """
    Fetch inference provider information from HuggingFace API and generate code template.
    
    Args:
        model_id: The HuggingFace model ID (e.g., "moonshotai/Kimi-K2-Thinking")
    
    Returns:
        The code snippet if model has inference providers, None otherwise
    """
    try:
        # Fetch trending models data from HuggingFace API
        response = requests.get("https://huggingface.co/api/trending", timeout=10)
        
        if response.status_code != 200:
            print(f"Failed to fetch trending models API: HTTP {response.status_code}")
            return None
        
        trending_data = response.json()
        recently_trending = trending_data.get("recentlyTrending", [])
        
        # Find the specific model in trending data
        model_info = None
        for item in recently_trending:
            repo_data = item.get("repoData", {})
            if repo_data.get("id") == model_id:
                model_info = repo_data
                break
        
        # If not found in trending, try to get model info directly from API
        if not model_info:
            try:
                api = HfApi()
                info = api.model_info(model_id)
                pipeline_tag = getattr(info, "pipeline_tag", None)
                
                # Check if model has inference providers via model info
                # Note: The direct API might not have availableInferenceProviders
                # In this case, we'll generate a generic template
                has_inference = pipeline_tag is not None
                
                if has_inference:
                    return _generate_inference_code_template(model_id, pipeline_tag, True)
            except Exception as e:
                print(f"Could not fetch model info for {model_id}: {e}")
                return None
        else:
            # Extract pipeline tag and inference providers info
            pipeline_tag = model_info.get("pipeline_tag")
            inference_providers = model_info.get("availableInferenceProviders", [])
            has_inference_providers = len(inference_providers) > 0
            
            # Generate code template based on pipeline tag
            return _generate_inference_code_template(model_id, pipeline_tag, has_inference_providers)
        
        return None
        
    except Exception as e:
        print(f"Error fetching inference provider code: {e}")
        return None


# Global storage for code alternatives (used when both inference and local code are available)
_model_code_alternatives = {}


def store_model_code_alternatives(model_id: str, inference_code: Optional[str], local_code: Optional[str]):
    """Store both code alternatives for a model for later retrieval."""
    global _model_code_alternatives
    _model_code_alternatives[model_id] = {
        'inference': inference_code,
        'local': local_code
    }


def get_model_code_alternatives(model_id: str) -> Dict[str, Optional[str]]:
    """Retrieve stored code alternatives for a model."""
    global _model_code_alternatives
    return _model_code_alternatives.get(model_id, {'inference': None, 'local': None})


def import_model_from_hf(model_id: str, prefer_local: bool = False) -> Tuple[str, str, str, str]:
    """
    Import a HuggingFace model by ID and extract code snippet.
    Tries to fetch both inference provider code and transformers/diffusers code from README.
    
    Args:
        model_id: The HuggingFace model ID
        prefer_local: If True and both options available, return local code instead of inference code
    
    Returns: (status, code, language, model_url)
    """
    if not model_id or model_id == "":
        return "Please select a model.", "", "python", ""
    
    # Build model URL
    model_url = f"https://huggingface.co/{model_id}"
    
    # Try to fetch both types of code
    inference_code = _fetch_inference_provider_code(model_id)
    
    # Also try to extract transformers/diffusers code from README
    readme_status, readme_code, _ = import_repo_to_app(model_url)
    has_readme_code = readme_code and ("transformers" in readme_code or "diffusers" in readme_code)
    
    # Store both alternatives for later switching
    store_model_code_alternatives(model_id, inference_code, readme_code if has_readme_code else None)
    
    # Build status message and code based on what's available
    if inference_code and has_readme_code:
        # Both available - provide choice
        if prefer_local:
            status = f"""✅ **Found multiple code options for `{model_id}`**

**Currently showing:** Local Transformers/Diffusers Code (Option 2) 💻

**Option 1: Inference Provider Code (Serverless)** ⚡
- Uses HuggingFace Inference API (serverless, pay-per-use)
- No GPU required, instant startup
- Requires `HF_TOKEN` environment variable

**Option 2: Local Transformers/Diffusers Code (Currently Active)** 💻
- Runs locally on your hardware
- Requires GPU for optimal performance
- Full control over model parameters

---

To switch to inference provider code, click the button below or ask: "Show me the inference provider code instead"
"""
            code = readme_code
        else:
            status = f"""✅ **Found multiple code options for `{model_id}`**

**Currently showing:** Inference Provider Code (Option 1) ⚡ *Recommended*

**Option 1: Inference Provider Code (Serverless - Currently Active)** ⚡
- Uses HuggingFace Inference API (serverless, pay-per-use)
- No GPU required, instant startup
- Requires `HF_TOKEN` environment variable

**Option 2: Local Transformers/Diffusers Code** 💻
- Runs locally on your hardware
- Requires GPU for optimal performance
- Full control over model parameters

---

To switch to local transformers/diffusers code, click the button below or ask: "Show me the local transformers code instead"
"""
            code = inference_code
        
        language = "gradio"
        return status, code, language, model_url
        
    elif inference_code:
        # Only inference provider code available
        status = f"✅ Imported inference provider code for `{model_id}` (serverless inference)"
        language = "gradio"
        return status, inference_code, language, model_url
        
    elif has_readme_code:
        # Only README code available
        status = f"✅ Imported transformers/diffusers code from README for `{model_id}` (local inference)"
        language = "gradio"
        return status, readme_code, language, model_url
        
    else:
        # No code found
        status = f"⚠️ No inference provider or transformers/diffusers code found for `{model_id}`"
        return status, "", "python", model_url


def switch_model_code_type(model_id: str, current_code: str) -> Tuple[str, str]:
    """
    Switch between inference provider code and local transformers/diffusers code.
    
    Args:
        model_id: The model ID
        current_code: The currently displayed code
    
    Returns: (status_message, new_code)
    """
    alternatives = get_model_code_alternatives(model_id)
    inference_code = alternatives['inference']
    local_code = alternatives['local']
    
    if not inference_code and not local_code:
        return "⚠️ No alternative code available for this model.", current_code
    
    # Determine which code is currently shown
    is_showing_inference = current_code == inference_code
    
    if is_showing_inference and local_code:
        # Switch to local code
        status = f"✅ Switched to **Local Transformers/Diffusers Code** for `{model_id}` 💻\n\nThis code runs locally on your hardware."
        return status, local_code
    elif not is_showing_inference and inference_code:
        # Switch to inference provider code
        status = f"✅ Switched to **Inference Provider Code** for `{model_id}` ⚡\n\nThis code uses serverless HuggingFace Inference API."
        return status, inference_code
    else:
        return "⚠️ Alternative code type not available for this model.", current_code


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

