"""
Standalone deployment utilities for publishing to HuggingFace Spaces.
No Gradio dependencies - can be used in backend API.
"""
import os
import re
import json
import uuid
import tempfile
import shutil
import ast
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from huggingface_hub import HfApi
from backend_models import get_inference_client, get_real_model_id
from backend_parsers import (
    parse_transformers_js_output,
    parse_html_code,
    parse_python_requirements,
    parse_multi_file_python_output,
    parse_react_output,
    strip_tool_call_markers,
    remove_code_block,
    extract_import_statements,
    generate_requirements_txt_with_llm,
    enforce_critical_versions
)


def prettify_comfyui_json_for_html(json_content: str) -> str:
    """Convert ComfyUI JSON to stylized HTML display with download button"""
    try:
        # Parse and prettify the JSON
        parsed_json = json.loads(json_content)
        prettified_json = json.dumps(parsed_json, indent=2, ensure_ascii=False)
        
        # Create Apple-style HTML wrapper
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ComfyUI Workflow</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', system-ui, sans-serif;
            background-color: #000000;
            color: #f5f5f7;
            line-height: 1.6;
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding: 40px 20px;
        }}
        .header h1 {{
            font-size: 48px;
            font-weight: 600;
            color: #ffffff;
            margin-bottom: 12px;
            letter-spacing: -0.02em;
        }}
        .header p {{
            font-size: 18px;
            color: #86868b;
            font-weight: 400;
        }}
        .controls {{
            display: flex;
            gap: 12px;
            margin-bottom: 24px;
            justify-content: center;
        }}
        .btn {{
            padding: 12px 24px;
            border: none;
            border-radius: 24px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            font-family: inherit;
        }}
        .btn-primary {{
            background: #ffffff;
            color: #000000;
        }}
        .btn-primary:hover {{
            background: #f5f5f7;
            transform: scale(0.98);
        }}
        .btn-secondary {{
            background: #1d1d1f;
            color: #f5f5f7;
            border: 1px solid #424245;
        }}
        .btn-secondary:hover {{
            background: #2d2d2f;
            transform: scale(0.98);
        }}
        .json-container {{
            background-color: #1d1d1f;
            border-radius: 16px;
            padding: 32px;
            overflow-x: auto;
            border: 1px solid #424245;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }}
        pre {{
            margin: 0;
            font-family: 'SF Mono', 'Monaco', 'Menlo', 'Consolas', monospace;
            font-size: 13px;
            line-height: 1.6;
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
        .success {{
            color: #30d158;
        }}
        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 32px;
            }}
            .controls {{
                flex-direction: column;
            }}
            .json-container {{
                padding: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ComfyUI Workflow</h1>
            <p>View and download your workflow JSON</p>
        </div>
        
        <div class="controls">
            <button class="btn btn-primary" onclick="downloadJSON()">Download JSON</button>
            <button class="btn btn-secondary" onclick="copyToClipboard()">Copy to Clipboard</button>
        </div>
        
        <div class="json-container">
            <pre id="json-content">{prettified_json}</pre>
        </div>
    </div>

    <script>
        function copyToClipboard() {{
            const jsonContent = document.getElementById('json-content').textContent;
            navigator.clipboard.writeText(jsonContent).then(() => {{
                const btn = event.target;
                const originalText = btn.textContent;
                btn.textContent = 'Copied!';
                btn.classList.add('success');
                setTimeout(() => {{
                    btn.textContent = originalText;
                    btn.classList.remove('success');
                }}, 2000);
            }}).catch(err => {{
                alert('Failed to copy to clipboard');
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
            
            const btn = event.target;
            const originalText = btn.textContent;
            btn.textContent = 'Downloaded!';
            btn.classList.add('success');
            setTimeout(() => {{
                btn.textContent = originalText;
                btn.classList.remove('success');
            }}, 2000);
        }}

        // Add syntax highlighting
        function highlightJSON() {{
            const content = document.getElementById('json-content');
            let html = content.innerHTML;
            
            // Highlight different JSON elements
            html = html.replace(/"([^"]+)":/g, '<span class="json-key">"$1":</span>');
            html = html.replace(/: "([^"]*)"/g, ': <span class="json-string">"$1"</span>');
            html = html.replace(/: (-?\\d+\\.?\\d*)/g, ': <span class="json-number">$1</span>');
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
        # If it's not valid JSON, return as-is wrapped in basic HTML
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ComfyUI Workflow</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif;
            background-color: #000000;
            color: #f5f5f7;
            padding: 40px;
        }}
        pre {{
            background: #1d1d1f;
            padding: 24px;
            border-radius: 12px;
            overflow-x: auto;
        }}
    </style>
</head>
<body>
    <h1>ComfyUI Workflow</h1>
    <p>Error: Invalid JSON format</p>
    <pre>{json_content}</pre>
</body>
</html>"""
    except Exception as e:
        print(f"Error prettifying ComfyUI JSON: {e}")
        return json_content


# Note: parse_transformers_js_output, parse_python_requirements, strip_tool_call_markers,
# remove_code_block, extract_import_statements, generate_requirements_txt_with_llm,
# and parse_multi_file_python_output are now imported from backend_parsers.py


def is_streamlit_code(code: str) -> bool:
    """Check if code is Streamlit"""
    return 'import streamlit' in code or 'streamlit.run' in code


def is_gradio_code(code: str) -> bool:
    """Check if code is Gradio or Daggr"""
    return 'import gradio' in code or 'gr.' in code or 'import daggr' in code or 'from daggr' in code


def detect_sdk_from_code(code: str, language: str) -> str:
    """Detect the appropriate SDK from code and language"""
    if language == "html":
        return "static"
    elif language == "transformers.js":
        return "static"
    elif language == "comfyui":
        return "static"
    elif language == "react":
        return "docker"
    elif language == "streamlit" or is_streamlit_code(code):
        return "docker"
    elif language == "gradio" or language == "daggr" or is_gradio_code(code):
        return "gradio"
    else:
        return "gradio"  # Default


def add_anycoder_tag_to_readme(api, repo_id: str, app_port: Optional[int] = None, sdk: Optional[str] = None) -> None:
    """
    Download existing README, add anycoder tag and app_port if needed, and upload back.
    Preserves all existing README content and frontmatter.
    
    Args:
        api: HuggingFace API client
        repo_id: Repository ID (username/space-name)
        app_port: Optional port number to set for Docker spaces (e.g., 7860)
        sdk: Optional SDK type (e.g., 'gradio', 'streamlit', 'docker', 'static')
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
                
                # For Gradio spaces, always set sdk_version to 6.0.2
                if sdk == 'gradio':
                    if 'sdk_version:' in frontmatter:
                        # Update existing sdk_version
                        frontmatter = re.sub(r'sdk_version:\s*[^\n]+', 'sdk_version: 6.0.2', frontmatter)
                        print(f"[README] Updated sdk_version to 6.0.2 for Gradio space")
                    else:
                        # Add sdk_version
                        frontmatter += '\nsdk_version: 6.0.2'
                        print(f"[README] Added sdk_version: 6.0.2 for Gradio space")
                
                # Reconstruct the README
                new_content = f"---\n{frontmatter}\n---{body}"
            else:
                # Malformed frontmatter, just add tags at the end of frontmatter
                new_content = content.replace('---', '---\ntags:\n- anycoder\n---', 1)
        else:
            # No frontmatter, add it at the beginning
            app_port_line = f'\napp_port: {app_port}' if app_port else ''
            sdk_version_line = '\nsdk_version: 6.0.2' if sdk == 'gradio' else ''
            new_content = f"---\ntags:\n- anycoder{app_port_line}{sdk_version_line}\n---\n\n{content}"
        
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
        
        os.unlink(temp_path)
        
    except Exception as e:
        print(f"Warning: Could not modify README.md to add anycoder tag: {e}")


def create_dockerfile_for_streamlit(space_name: str) -> str:
    """Create Dockerfile for Streamlit app"""
    return f"""FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7860

CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]
"""


def create_dockerfile_for_react(space_name: str) -> str:
    """Create Dockerfile for React app"""
    return f"""FROM node:18-slim

# Use existing node user
USER node
ENV HOME=/home/node
ENV PATH=/home/node/.local/bin:$PATH

WORKDIR /home/node/app

COPY --chown=node:node package*.json ./
RUN npm install

COPY --chown=node:node . .
RUN npm run build

EXPOSE 7860

CMD ["npm", "start", "--", "-p", "7860"]
"""


def extract_space_id_from_history(history: Optional[List], username: Optional[str] = None) -> Optional[str]:
    """
    Extract existing space ID from chat history (for updates after followups/imports)
    
    Args:
        history: Chat history (list of lists [[role, content], ...] or list of dicts)
        username: Current username (to verify ownership of imported spaces)
    
    Returns:
        Space ID (username/space-name) if found, None otherwise
    """
    if not history:
        return None
    
    import re
    existing_space = None
    
    # Look through history for previous deployments or imports
    for msg in history:
        # Handle both list format [[role, content], ...] and dict format [{'role': ..., 'content': ...}, ...]
        if isinstance(msg, list) and len(msg) >= 2:
            role = msg[0]
            content = msg[1]
        elif isinstance(msg, dict):
            role = msg.get('role', '')
            content = msg.get('content', '')
        else:
            continue
        
        # Check assistant messages for deployment confirmations
        if role == 'assistant':
            # Look for various deployment success patterns (case-insensitive)
            content_lower = content.lower()
            has_deployment_indicator = (
                "deployed" in content_lower or 
                "updated" in content_lower or
                "✅" in content  # Check mark often indicates deployment success
            )
            
            if has_deployment_indicator:
                # Look for space URL pattern
                match = re.search(r'huggingface\.co/spaces/([^/\s\)]+/[^/\s\)]+)', content)
                if match:
                    existing_space = match.group(1)
                    print(f"[Extract Space] Found existing space: {existing_space}")
                    break
        
        # Check user messages for imports
        elif role == 'user':
            if "import" in content.lower() and "space" in content.lower():
                # Extract space name from import message
                match = re.search(r'huggingface\.co/spaces/([^/\s\)]+/[^/\s\)]+)', content)
                if match:
                    imported_space = match.group(1)
                    # Only use imported space if user owns it (can update it)
                    if username and imported_space.startswith(f"{username}/"):
                        existing_space = imported_space
                        break
                    # If user doesn't own the imported space, we'll create a new one
                    # (existing_space remains None, triggering new deployment)
    
    return existing_space


def deploy_to_huggingface_space(
    code: str,
    language: str,
    space_name: Optional[str] = None,
    token: Optional[str] = None,
    username: Optional[str] = None,
    description: Optional[str] = None,
    private: bool = False,
    existing_repo_id: Optional[str] = None,
    commit_message: Optional[str] = None,
    history: Optional[List[Dict]] = None
) -> Tuple[bool, str, Optional[str]]:
    """
    Deploy code to HuggingFace Spaces (create new or update existing)
    
    Args:
        code: Generated code to deploy
        language: Target language/framework (html, gradio, streamlit, react, transformers.js, comfyui)
        space_name: Name for the space (auto-generated if None, ignored if existing_repo_id provided)
        token: HuggingFace API token
        username: HuggingFace username
        description: Space description
        private: Whether to make the space private (only for new spaces)
        existing_repo_id: If provided (username/space-name), updates this space instead of creating new one
        commit_message: Custom commit message (defaults to "Deploy from anycoder" or "Update from anycoder")
        history: Chat history (list of dicts with 'role' and 'content') - used to detect followups/imports
    
    Returns:
        Tuple of (success: bool, message: str, space_url: Optional[str])
    """
    if not token:
        token = os.getenv("HF_TOKEN")
        if not token:
            return False, "No HuggingFace token provided", None
    
    try:
        api = HfApi(token=token)
        
        # Get username if not provided (needed for history tracking)
        if not username:
            try:
                user_info = api.whoami()
                username = user_info.get("name") or user_info.get("preferred_username") or "user"
            except Exception as e:
                pass  # Will handle later if needed
        
        # Check history for existing space if not explicitly provided
        # This enables automatic updates for followup prompts and imported spaces
        if not existing_repo_id and history:
            existing_repo_id = extract_space_id_from_history(history, username)
            if existing_repo_id:
                print(f"[Deploy] Detected existing space from history: {existing_repo_id}")
        
        # Determine if this is an update or new deployment
        is_update = existing_repo_id is not None
        
        print(f"[Deploy] ========== DEPLOYMENT DECISION ==========")
        print(f"[Deploy] existing_repo_id provided: {existing_repo_id}")
        print(f"[Deploy] history provided: {history is not None} (length: {len(history) if history else 0})")
        print(f"[Deploy] username: {username}")
        print(f"[Deploy] is_update: {is_update}")
        print(f"[Deploy] language: {language}")
        print(f"[Deploy] ============================================")
        
        # For React space updates (followup changes), handle SEARCH/REPLACE blocks
        if is_update and language == "react":
            print(f"[Deploy] React space update - checking for search/replace blocks")
            
            # Import search/replace utilities
            from backend_search_replace import has_search_replace_blocks, parse_file_specific_changes, apply_search_replace_changes
            from huggingface_hub import hf_hub_download
            
            # Check if code contains search/replace blocks
            if has_search_replace_blocks(code):
                print(f"[Deploy] Detected SEARCH/REPLACE blocks - applying targeted changes")
                
                # Parse file-specific changes from code
                file_changes = parse_file_specific_changes(code)
                
                # Download existing files from the space
                try:
                    print(f"[Deploy] Downloading existing files from space: {existing_repo_id}")
                    
                    # Get list of files in the space
                    space_files = api.list_repo_files(repo_id=existing_repo_id, repo_type="space")
                    print(f"[Deploy] Found {len(space_files)} files in space: {space_files}")
                    
                    # Download relevant files (React/Next.js files)
                    react_file_patterns = ['.js', '.jsx', '.ts', '.tsx', '.css', '.json', 'Dockerfile']
                    existing_files = {}
                    
                    for file_path in space_files:
                        # Skip non-code files
                        if any(file_path.endswith(ext) or ext in file_path for ext in react_file_patterns):
                            try:
                                downloaded_path = hf_hub_download(
                                    repo_id=existing_repo_id,
                                    filename=file_path,
                                    repo_type="space",
                                    token=token
                                )
                                with open(downloaded_path, 'r', encoding='utf-8') as f:
                                    existing_files[file_path] = f.read()
                                print(f"[Deploy] Downloaded: {file_path} ({len(existing_files[file_path])} chars)")
                            except Exception as e:
                                print(f"[Deploy] Warning: Could not download {file_path}: {e}")
                    
                    if not existing_files:
                        print(f"[Deploy] Warning: No React files found in space, falling back to full deployment")
                    else:
                        # Apply search/replace changes to the appropriate files
                        updated_files = []
                        
                        # Check if changes are file-specific or global
                        if "__all__" in file_changes:
                            # Global changes - try to apply to all files
                            changes_text = file_changes["__all__"]
                            print(f"[Deploy] Applying global search/replace changes")
                            
                            # Try to apply to each file
                            for file_path, original_content in existing_files.items():
                                modified_content = apply_search_replace_changes(original_content, changes_text)
                                if modified_content != original_content:
                                    print(f"[Deploy] Modified {file_path}")
                                    success, msg = update_space_file(
                                        repo_id=existing_repo_id,
                                        file_path=file_path,
                                        content=modified_content,
                                        token=token,
                                        commit_message=commit_message or f"Update {file_path} from anycoder"
                                    )
                                    if success:
                                        updated_files.append(file_path)
                                    else:
                                        print(f"[Deploy] Warning: Failed to update {file_path}: {msg}")
                        else:
                            # File-specific changes
                            for filename, changes_text in file_changes.items():
                                # Find the file in existing files (handle both with/without directory prefix)
                                matching_file = None
                                for file_path in existing_files.keys():
                                    if file_path == filename or file_path.endswith('/' + filename):
                                        matching_file = file_path
                                        break
                                
                                if matching_file:
                                    original_content = existing_files[matching_file]
                                    modified_content = apply_search_replace_changes(original_content, changes_text)
                                    
                                    print(f"[Deploy] Applying changes to {matching_file}")
                                    success, msg = update_space_file(
                                        repo_id=existing_repo_id,
                                        file_path=matching_file,
                                        content=modified_content,
                                        token=token,
                                        commit_message=commit_message or f"Update {matching_file} from anycoder"
                                    )
                                    
                                    if success:
                                        updated_files.append(matching_file)
                                    else:
                                        print(f"[Deploy] Warning: Failed to update {matching_file}: {msg}")
                                else:
                                    print(f"[Deploy] Warning: File {filename} not found in space")
                        
                        if updated_files:
                            space_url = f"https://huggingface.co/spaces/{existing_repo_id}"
                            files_list = ", ".join(updated_files)
                            return True, f"✅ Updated {len(updated_files)} file(s): {files_list}! View at: {space_url}", space_url
                        else:
                            return False, "No files were updated", None
                    
                except Exception as e:
                    print(f"[Deploy] Error applying search/replace changes: {e}")
                    import traceback
                    traceback.print_exc()
                    # Fall through to normal deployment
            else:
                print(f"[Deploy] No SEARCH/REPLACE blocks detected, proceeding with full file update")
                # Fall through to normal React deployment below
        
        # For Gradio space updates (import/redesign), update .py files and upload all new files
        if is_update and language in ["gradio", "daggr"]:
            print(f"[Deploy] Gradio space update - updating .py files and uploading any new files")
            
            # Parse the code to get all files
            files = parse_multi_file_python_output(code)
            
            # Fallback if no files parsed
            if not files:
                print(f"[Deploy] No file markers found, using entire code as app.py")
                cleaned_code = remove_code_block(code)
                files['app.py'] = cleaned_code
            
            if not files:
                return False, "Error: No files found in generated code", None
            
            print(f"[Deploy] Generated {len(files)} file(s): {list(files.keys())}")
            
            # For redesign operations, ONLY update app.py to preserve other helper files
            # Detect redesign from commit message OR from history (user prompt contains "redesign")
            is_redesign = False
            if commit_message and "redesign" in commit_message.lower():
                is_redesign = True
            elif history:
                # Check last user message for "redesign" keyword
                for role, content in reversed(history):
                    if role == "user" and content and "redesign" in content.lower():
                        is_redesign = True
                        break
            
            if is_redesign:
                print(f"[Deploy] Redesign operation detected - filtering to ONLY app.py")
                app_py_content = files.get('app.py')
                if not app_py_content:
                    return False, "Error: No app.py found in redesign output", None
                files = {'app.py': app_py_content}
                print(f"[Deploy] Will only update app.py ({len(app_py_content)} chars)")
            
            # Upload all generated files (the LLM is instructed to only output .py files,
            # but if it creates new assets/data files, we should upload those too)
            # This approach updates .py files and adds any new files without touching
            # existing non-.py files that weren't generated
            updated_files = []
            for file_path, content in files.items():
                print(f"[Deploy] Uploading {file_path} ({len(content)} chars)")
                success, msg = update_space_file(
                    repo_id=existing_repo_id,
                    file_path=file_path,
                    content=content,
                    token=token,
                    commit_message=commit_message or f"Update {file_path} from anycoder"
                )
                
                if success:
                    updated_files.append(file_path)
                else:
                    print(f"[Deploy] Warning: Failed to update {file_path}: {msg}")
            
            if updated_files:
                space_url = f"https://huggingface.co/spaces/{existing_repo_id}"
                files_list = ", ".join(updated_files)
                return True, f"✅ Updated {len(updated_files)} file(s): {files_list}! View at: {space_url}", space_url
            else:
                return False, "Failed to update any files", None
        
        if is_update:
            # Use existing repo
            repo_id = existing_repo_id
            space_name = existing_repo_id.split('/')[-1]
            if '/' in existing_repo_id:
                username = existing_repo_id.split('/')[0]
            elif not username:
                # Get username if still not available
                try:
                    user_info = api.whoami()
                    username = user_info.get("name") or user_info.get("preferred_username") or "user"
                except Exception as e:
                    return False, f"Failed to get user info: {str(e)}", None
        else:
            # Get username if not provided
            if not username:
                try:
                    user_info = api.whoami()
                    username = user_info.get("name") or user_info.get("preferred_username") or "user"
                except Exception as e:
                    return False, f"Failed to get user info: {str(e)}", None
            
            # Generate space name if not provided or empty
            if not space_name or space_name.strip() == "":
                space_name = f"anycoder-{uuid.uuid4().hex[:8]}"
                print(f"[Deploy] Auto-generated space name: {space_name}")
            
            # Clean space name (no spaces, lowercase, alphanumeric + hyphens)
            space_name = re.sub(r'[^a-z0-9-]', '-', space_name.lower())
            space_name = re.sub(r'-+', '-', space_name).strip('-')
            
            # Ensure space_name is not empty after cleaning
            if not space_name:
                space_name = f"anycoder-{uuid.uuid4().hex[:8]}"
                print(f"[Deploy] Space name was empty after cleaning, regenerated: {space_name}")
            
            repo_id = f"{username}/{space_name}"
            print(f"[Deploy] Using repo_id: {repo_id}")
        
        # Detect SDK
        sdk = detect_sdk_from_code(code, language)
        
        # Create temporary directory for files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Parse code based on language
            app_port = None  # Track if we need app_port for Docker spaces
            use_individual_uploads = False  # Flag for transformers.js
            
            if language == "transformers.js":
                try:
                    files = parse_transformers_js_output(code)
                    print(f"[Deploy] Parsed transformers.js files: {list(files.keys())}")
                    
                    # Log file sizes for debugging
                    for fname, fcontent in files.items():
                        if fcontent:
                            print(f"[Deploy] {fname}: {len(fcontent)} characters")
                        else:
                            print(f"[Deploy] {fname}: EMPTY")
                    
                    # Validate all three files are present in the dict
                    required_files = {'index.html', 'index.js', 'style.css'}
                    missing_from_dict = required_files - set(files.keys())
                    
                    if missing_from_dict:
                        error_msg = f"Failed to parse required files: {', '.join(sorted(missing_from_dict))}. "
                        error_msg += f"Parsed files: {', '.join(files.keys()) if files else 'none'}. "
                        error_msg += "Transformers.js apps require all three files (index.html, index.js, style.css). Please regenerate using the correct format."
                        print(f"[Deploy] {error_msg}")
                        return False, error_msg, None
                    
                    # Validate files have actual content (not empty or whitespace-only)
                    empty_files = [name for name in required_files if not files.get(name, '').strip()]
                    if empty_files:
                        error_msg = f"Empty file content detected: {', '.join(sorted(empty_files))}. "
                        error_msg += "All three files must contain actual code. Please regenerate with complete content."
                        print(f"[Deploy] {error_msg}")
                        return False, error_msg, None
                    
                    # Write transformers.js files to temp directory
                    for filename, content in files.items():
                        file_path = temp_path / filename
                        print(f"[Deploy] Writing {filename} ({len(content)} chars) to {file_path}")
                        # Use text mode - Python handles encoding automatically
                        if filename == "requirements.txt":
                            content = enforce_critical_versions(content)
                        file_path.write_text(content, encoding='utf-8')
                        # Verify the write was successful
                        written_size = file_path.stat().st_size
                        print(f"[Deploy] Verified {filename}: {written_size} bytes on disk")
                    
                    # For transformers.js, we'll upload files individually (not via upload_folder)
                    use_individual_uploads = True
                    
                except Exception as e:
                    print(f"[Deploy] Error parsing transformers.js: {e}")
                    import traceback
                    traceback.print_exc()
                    return False, f"Error parsing transformers.js output: {str(e)}", None
                
            elif language == "html":
                html_code = parse_html_code(code)
                (temp_path / "index.html").write_text(html_code, encoding='utf-8')
                
            elif language == "comfyui":
                # ComfyUI is JSON, wrap in stylized HTML viewer with download button
                html_code = prettify_comfyui_json_for_html(code)
                (temp_path / "index.html").write_text(html_code, encoding='utf-8')
                
            elif language in ["gradio", "streamlit", "daggr"]:
                files = parse_multi_file_python_output(code)
                
                # Fallback: if no files parsed (missing === markers), treat entire code as app.py
                if not files:
                    print(f"[Deploy] No file markers found in {language} code, using entire code as app.py")
                    # Clean up code blocks if present
                    cleaned_code = remove_code_block(code)
                    # Determine app filename based on language
                    app_filename = "streamlit_app.py" if language == "streamlit" else "app.py"
                    files[app_filename] = cleaned_code
                
                # Write Python files (create subdirectories if needed)
                for filename, content in files.items():
                    file_path = temp_path / filename
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    if filename == "requirements.txt":
                        content = enforce_critical_versions(content)
                    file_path.write_text(content, encoding='utf-8')
                
                # Ensure requirements.txt exists - generate from imports if missing
                if "requirements.txt" not in files:
                    # Get the main app file (app.py for gradio, streamlit_app.py or app.py for streamlit)
                    main_app = files.get('streamlit_app.py') or files.get('app.py', '')
                    if main_app:
                        print(f"[Deploy] Generating requirements.txt from imports in {language} app")
                        import_statements = extract_import_statements(main_app)
                        requirements_content = generate_requirements_txt_with_llm(import_statements)
                        (temp_path / "requirements.txt").write_text(requirements_content, encoding='utf-8')
                        print(f"[Deploy] Generated requirements.txt with {len(requirements_content.splitlines())} lines")
                    else:
                        # Fallback to minimal requirements if no app file found
                        if language == "gradio":
                            (temp_path / "requirements.txt").write_text("gradio>=4.0.0\n", encoding='utf-8')
                        elif language == "streamlit":
                            (temp_path / "requirements.txt").write_text("streamlit>=1.30.0\n", encoding='utf-8')
                        elif language == "daggr":
                            (temp_path / "requirements.txt").write_text("daggr>=0.5.4\ngradio>=6.0.2\n", encoding='utf-8')
                
                # Create Dockerfile if needed
                if sdk == "docker":
                    if language == "streamlit":
                        dockerfile = create_dockerfile_for_streamlit(space_name)
                        (temp_path / "Dockerfile").write_text(dockerfile, encoding='utf-8')
                    app_port = 7860  # Set app_port for Docker spaces
                    use_individual_uploads = True  # Streamlit uses individual file uploads
                
            elif language == "react":
                # Parse React output to get all files (uses === filename === markers)
                files = parse_react_output(code)
                
                if not files:
                    return False, "Error: Could not parse React output", None
                
                # If Dockerfile is missing, use template
                if 'Dockerfile' not in files:
                    dockerfile = create_dockerfile_for_react(space_name)
                    files['Dockerfile'] = dockerfile
                
                # Write all React files (create subdirectories if needed)
                for filename, content in files.items():
                    file_path = temp_path / filename
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(content, encoding='utf-8')
                
                app_port = 7860  # Set app_port for Docker spaces
                use_individual_uploads = True  # React uses individual file uploads
            
            else:
                # Default: treat as Gradio app
                files = parse_multi_file_python_output(code)
                
                # Fallback: if no files parsed (missing === markers), treat entire code as app.py
                if not files:
                    print(f"[Deploy] No file markers found in default (gradio) code, using entire code as app.py")
                    # Clean up code blocks if present
                    cleaned_code = remove_code_block(code)
                    files['app.py'] = cleaned_code
                
                # Write files (create subdirectories if needed)
                for filename, content in files.items():
                    file_path = temp_path / filename
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    if filename == "requirements.txt":
                        content = enforce_critical_versions(content)
                    file_path.write_text(content, encoding='utf-8')
                
                # Generate requirements.txt from imports if missing
                if "requirements.txt" not in files:
                    main_app = files.get('app.py', '')
                    if main_app:
                        print(f"[Deploy] Generating requirements.txt from imports in default app")
                        import_statements = extract_import_statements(main_app)
                        requirements_content = generate_requirements_txt_with_llm(import_statements)
                        (temp_path / "requirements.txt").write_text(requirements_content, encoding='utf-8')
                        print(f"[Deploy] Generated requirements.txt with {len(requirements_content.splitlines())} lines")
                    else:
                        # Fallback to minimal requirements if no app file found
                        if language == "daggr":
                            (temp_path / "requirements.txt").write_text("daggr>=0.5.4\ngradio>=6.0.2\n", encoding='utf-8')
                        else:
                            (temp_path / "requirements.txt").write_text("gradio>=4.0.0\n", encoding='utf-8')
            
            # Don't create README - HuggingFace will auto-generate it
            # We'll add the anycoder tag after deployment
            
            # ONLY create repo for NEW deployments of non-Docker, non-transformers.js spaces
            # Docker and transformers.js handle repo creation separately below
            # This matches the Gradio version logic (line 1256 in ui.py)
            if not is_update and sdk != "docker" and language not in ["transformers.js"]:
                print(f"[Deploy] Creating NEW {sdk} space: {repo_id}")
                try:
                    api.create_repo(
                        repo_id=repo_id,
                        repo_type="space",
                        space_sdk=sdk,
                        private=private,
                        exist_ok=True
                    )
                except Exception as e:
                    return False, f"Failed to create space: {str(e)}", None
            elif is_update:
                print(f"[Deploy] UPDATING existing space: {repo_id} (skipping create_repo)")
            
            # Handle transformers.js spaces (create repo via duplicate_space)
            if language == "transformers.js":
                if not is_update:
                    print(f"[Deploy] Creating NEW transformers.js space via template duplication")
                    print(f"[Deploy] space_name value: '{space_name}' (type: {type(space_name)})")
                    
                    # Safety check for space_name
                    if not space_name:
                        return False, "Internal error: space_name is None after generation", None
                    
                    try:
                        from huggingface_hub import duplicate_space
                        
                        # duplicate_space expects just the space name (not full repo_id)
                        # Use strip() to clean the space name
                        clean_space_name = space_name.strip()
                        print(f"[Deploy] Attempting to duplicate template space to: {clean_space_name}")
                        
                        duplicated_repo = duplicate_space(
                            from_id="static-templates/transformers.js",
                            to_id=clean_space_name,
                            token=token,
                            exist_ok=True
                        )
                        print(f"[Deploy] Template duplication result: {duplicated_repo} (type: {type(duplicated_repo)})")
                    except Exception as e:
                        print(f"[Deploy] Exception during duplicate_space: {type(e).__name__}: {str(e)}")
                        
                        # Check if space actually exists (success despite error)
                        space_exists = False
                        try:
                            if api.space_info(repo_id):
                                space_exists = True
                        except:
                            pass

                        # Handle RepoUrl object "errors"
                        error_msg = str(e)
                        if ("'url'" in error_msg or "RepoUrl" in error_msg) and space_exists:
                            print(f"[Deploy] Space exists despite RepoUrl error, continuing with deployment")
                        else:
                            # Fallback to regular create_repo
                            print(f"[Deploy] Template duplication failed, attempting fallback to create_repo: {e}")
                            try:
                                api.create_repo(
                                    repo_id=repo_id,
                                    repo_type="space",
                                    space_sdk="static",
                                    private=private,
                                    exist_ok=True
                                )
                                print(f"[Deploy] Fallback create_repo successful")
                            except Exception as e2:
                                return False, f"Failed to create transformers.js space (both duplication and fallback failed): {str(e2)}", None
                else:
                    # For updates, verify we can access the existing space
                    try:
                        space_info = api.space_info(repo_id)
                        if not space_info:
                            return False, f"Could not access space {repo_id} for update", None
                    except Exception as e:
                        return False, f"Cannot update space {repo_id}: {str(e)}", None
            
            # Handle Docker spaces (React/Streamlit) - create repo separately
            elif sdk == "docker" and language in ["streamlit", "react"]:
                if not is_update:
                    print(f"[Deploy] Creating NEW Docker space for {language}: {repo_id}")
                    try:
                        from huggingface_hub import create_repo as hf_create_repo
                        hf_create_repo(
                            repo_id=repo_id,
                            repo_type="space",
                            space_sdk="docker",
                            token=token,
                            exist_ok=True
                        )
                    except Exception as e:
                        return False, f"Failed to create Docker space: {str(e)}", None
            
            # Upload files
            if not commit_message:
                commit_message = "Update from anycoder" if is_update else "Deploy from anycoder"
            
            try:
                if language == "transformers.js":
                    # Special handling for transformers.js - create NEW temp files for each upload
                    # This matches the working pattern in ui.py
                    import time
                    
                    # Get the parsed files from earlier
                    files_to_upload = [
                        ("index.html", files.get('index.html')),
                        ("index.js", files.get('index.js')),
                        ("style.css", files.get('style.css'))
                    ]
                    
                    max_attempts = 3
                    for file_name, file_content in files_to_upload:
                        if not file_content:
                            return False, f"Missing content for {file_name}", None
                        
                        success = False
                        last_error = None
                        
                        for attempt in range(max_attempts):
                            temp_file_path = None
                            try:
                                # Create a NEW temp file for this upload (matches Gradio version approach)
                                print(f"[Deploy] Creating temp file for {file_name} with {len(file_content)} chars")
                                # Use text mode "w" - lets Python handle encoding automatically (better emoji support)
                                with tempfile.NamedTemporaryFile("w", suffix=f".{file_name.split('.')[-1]}", delete=False) as f:
                                    f.write(file_content)
                                    temp_file_path = f.name
                                # File is now closed and flushed, safe to upload
                                
                                # Upload the file without commit_message (HF handles this for spaces)
                                api.upload_file(
                                    path_or_fileobj=temp_file_path,
                                    path_in_repo=file_name,
                                    repo_id=repo_id,
                                    repo_type="space"
                                )
                                success = True
                                print(f"[Deploy] Successfully uploaded {file_name}")
                                break
                                
                            except Exception as e:
                                last_error = e
                                error_str = str(e)
                                print(f"[Deploy] Upload error for {file_name}: {error_str}")
                                if "403" in error_str or "Forbidden" in error_str:
                                    return False, f"Permission denied uploading {file_name}. Check your token has write access to {repo_id}.", None
                                
                                if attempt < max_attempts - 1:
                                    time.sleep(2)  # Wait before retry
                                    print(f"[Deploy] Retry {attempt + 1}/{max_attempts} for {file_name}")
                            finally:
                                # Clean up temp file
                                if temp_file_path and os.path.exists(temp_file_path):
                                    os.unlink(temp_file_path)
                        
                        if not success:
                            return False, f"Failed to upload {file_name} after {max_attempts} attempts: {last_error}", None
                
                elif use_individual_uploads:
                    # For React, Streamlit: upload each file individually
                    import time
                    
                    # Get list of files to upload from temp directory
                    files_to_upload = []
                    for file_path in temp_path.rglob('*'):
                        if file_path.is_file():
                            # Get relative path from temp directory (use forward slashes for repo paths)
                            rel_path = file_path.relative_to(temp_path)
                            files_to_upload.append(str(rel_path).replace('\\', '/'))
                    
                    if not files_to_upload:
                        return False, "No files to upload", None
                    
                    print(f"[Deploy] Uploading {len(files_to_upload)} files individually: {files_to_upload}")
                    
                    max_attempts = 3
                    for filename in files_to_upload:
                        # Convert back to Path for filesystem operations
                        file_path = temp_path / filename.replace('/', os.sep)
                        if not file_path.exists():
                            return False, f"Failed to upload: {filename} not found", None
                        
                        # Upload with retry logic
                        success = False
                        last_error = None
                        
                        for attempt in range(max_attempts):
                            try:
                                # Upload without commit_message - HF API handles this for spaces
                                api.upload_file(
                                    path_or_fileobj=str(file_path),
                                    path_in_repo=filename,
                                    repo_id=repo_id,
                                    repo_type="space"
                                )
                                success = True
                                print(f"[Deploy] Successfully uploaded {filename}")
                                break
                            except Exception as e:
                                last_error = e
                                error_str = str(e)
                                print(f"[Deploy] Upload error for {filename}: {error_str}")
                                if "403" in error_str or "Forbidden" in error_str:
                                    return False, f"Permission denied uploading {filename}. Check your token has write access to {repo_id}.", None
                                if attempt < max_attempts - 1:
                                    time.sleep(2)  # Wait before retry
                                    print(f"[Deploy] Retry {attempt + 1}/{max_attempts} for {filename}")
                        
                        if not success:
                            return False, f"Failed to upload {filename} after {max_attempts} attempts: {last_error}", None
                else:
                    # For other languages, use upload_folder
                    print(f"[Deploy] Uploading folder to {repo_id}")
                    api.upload_folder(
                        folder_path=str(temp_path),
                        repo_id=repo_id,
                        repo_type="space"
                    )
            except Exception as e:
                return False, f"Failed to upload files: {str(e)}", None
            
            # After successful upload, modify the auto-generated README to add anycoder tag
            # For new spaces: HF auto-generates README, wait and modify it
            # For updates: README should already exist, just add tag if missing
            try:
                import time
                if not is_update:
                    time.sleep(2)  # Give HF time to generate README for new spaces
                add_anycoder_tag_to_readme(api, repo_id, app_port, sdk)
            except Exception as e:
                # Don't fail deployment if README modification fails
                print(f"Warning: Could not add anycoder tag to README: {e}")
            
            # For transformers.js updates, trigger a space restart to ensure changes take effect
            if is_update and language == "transformers.js":
                try:
                    api.restart_space(repo_id=repo_id)
                    print(f"[Deploy] Restarted space after update: {repo_id}")
                except Exception as restart_error:
                    # Don't fail the deployment if restart fails, just log it
                    print(f"Note: Could not restart space after update: {restart_error}")
            
            space_url = f"https://huggingface.co/spaces/{repo_id}"
            action = "Updated" if is_update else "Deployed"
            
            # Include the space URL in the message for history tracking
            # This allows future deployments to detect this as the existing space
            success_msg = f"✅ {action}! View your space at: {space_url}"
            
            return True, success_msg, space_url
            
    except Exception as e:
        print(f"[Deploy] Top-level exception caught: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, f"Deployment error: {str(e)}", None


def update_space_file(
    repo_id: str,
    file_path: str,
    content: str,
    token: Optional[str] = None,
    commit_message: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Update a single file in an existing HuggingFace Space
    
    Args:
        repo_id: Full repo ID (username/space-name)
        file_path: Path of file to update (e.g., "app.py")
        content: New file content
        token: HuggingFace API token
        commit_message: Commit message (default: "Update {file_path}")
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    if not token:
        token = os.getenv("HF_TOKEN")
        if not token:
            return False, "No HuggingFace token provided"
    
    try:
        api = HfApi(token=token)
        
        if not commit_message:
            commit_message = f"Update {file_path}"
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{file_path.split(".")[-1]}', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            api.upload_file(
                path_or_fileobj=temp_path,
                path_in_repo=file_path,
                repo_id=repo_id,
                repo_type="space",
                commit_message=commit_message
            )
            return True, f"✅ Successfully updated {file_path}"
        finally:
            os.unlink(temp_path)
            
    except Exception as e:
        return False, f"Failed to update file: {str(e)}"


def delete_space(
    repo_id: str,
    token: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Delete a HuggingFace Space
    
    Args:
        repo_id: Full repo ID (username/space-name)
        token: HuggingFace API token
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    if not token:
        token = os.getenv("HF_TOKEN")
        if not token:
            return False, "No HuggingFace token provided"
    
    try:
        api = HfApi(token=token)
        api.delete_repo(repo_id=repo_id, repo_type="space")
        return True, f"✅ Successfully deleted {repo_id}"
    except Exception as e:
        return False, f"Failed to delete space: {str(e)}"


def list_user_spaces(
    username: Optional[str] = None,
    token: Optional[str] = None
) -> Tuple[bool, str, Optional[List[Dict]]]:
    """
    List all spaces for a user
    
    Args:
        username: HuggingFace username (gets from token if None)
        token: HuggingFace API token
    
    Returns:
        Tuple of (success: bool, message: str, spaces: Optional[List[Dict]])
    """
    if not token:
        token = os.getenv("HF_TOKEN")
        if not token:
            return False, "No HuggingFace token provided", None
    
    try:
        api = HfApi(token=token)
        
        # Get username if not provided
        if not username:
            user_info = api.whoami()
            username = user_info.get("name") or user_info.get("preferred_username")
        
        # List spaces
        spaces = api.list_spaces(author=username)
        
        space_list = []
        for space in spaces:
            space_list.append({
                "id": space.id,
                "author": space.author,
                "name": getattr(space, 'name', space.id.split('/')[-1]),
                "sdk": getattr(space, 'sdk', 'unknown'),
                "private": getattr(space, 'private', False),
                "url": f"https://huggingface.co/spaces/{space.id}"
            })
        
        return True, f"Found {len(space_list)} spaces", space_list
        
    except Exception as e:
        return False, f"Failed to list spaces: {str(e)}", None


def duplicate_space_to_user(
    from_space_id: str,
    to_space_name: Optional[str] = None,
    token: Optional[str] = None,
    private: bool = False
) -> Tuple[bool, str, Optional[str]]:
    """
    Duplicate a HuggingFace Space to the user's account
    
    Args:
        from_space_id: Source space ID (username/space-name)
        to_space_name: Destination space name (just the name, not full ID)
        token: HuggingFace API token
        private: Whether the duplicated space should be private
    
    Returns:
        Tuple of (success: bool, message: str, space_url: Optional[str])
    """
    if not token:
        token = os.getenv("HF_TOKEN")
        if not token:
            return False, "No HuggingFace token provided", None
    
    try:
        from huggingface_hub import duplicate_space
        
        # Get username from token
        api = HfApi(token=token)
        user_info = api.whoami()
        username = user_info.get("name") or user_info.get("preferred_username") or "user"
        
        # Get original space info to detect hardware and SDK
        print(f"[Duplicate] Fetching info for {from_space_id}")
        original_hardware = None
        original_storage = None
        original_sdk = None
        try:
            original_space_info = api.space_info(from_space_id)
            # Get SDK type
            original_sdk = getattr(original_space_info, 'sdk', None)
            # Get runtime info
            runtime = getattr(original_space_info, 'runtime', None)
            if runtime:
                original_hardware = getattr(runtime, 'hardware', None)
                original_storage = getattr(runtime, 'storage', None)
            print(f"[Duplicate] Original space SDK: {original_sdk}, hardware: {original_hardware}, storage: {original_storage}")
        except Exception as e:
            print(f"[Duplicate] Could not fetch space info: {e}")
        
        # If no destination name provided, use original name
        if not to_space_name:
            # Extract original space name
            original_name = from_space_id.split('/')[-1]
            to_space_name = original_name
        
        # Clean space name
        to_space_name = re.sub(r'[^a-z0-9-]', '-', to_space_name.lower())
        to_space_name = re.sub(r'-+', '-', to_space_name).strip('-')
        
        # Construct full destination ID
        to_space_id = f"{username}/{to_space_name}"
        
        print(f"[Duplicate] Duplicating {from_space_id} to {to_space_id}")
        
        # Prepare duplicate_space parameters
        duplicate_params = {
            "from_id": from_space_id,
            "to_id": to_space_name,  # Just the name, not full ID
            "token": token,
            "exist_ok": True
        }
        
        # Hardware is REQUIRED by HF API for all space types when duplicating
        # Use detected hardware or default to cpu-basic
        hardware_to_use = original_hardware if original_hardware else "cpu-basic"
        duplicate_params["hardware"] = hardware_to_use
        print(f"[Duplicate] Hardware: {hardware_to_use} (SDK: {original_sdk}, original: {original_hardware})")
        
        # Storage is optional
        if original_storage and original_storage.get('requested'):
            duplicate_params["storage"] = original_storage.get('requested')
            print(f"[Duplicate] Storage: {original_storage.get('requested')}")
        
        # Only set private if explicitly requested
        if private:
            duplicate_params["private"] = private
        
        # Duplicate the space
        print(f"[Duplicate] Duplicating {from_space_id} to {username}/{to_space_name}")
        print(f"[Duplicate] Parameters: {list(duplicate_params.keys())}")
        
        try:
            duplicated_repo = duplicate_space(**duplicate_params)
        except Exception as dup_error:
            # Check if it's a zero-gpu hardware error
            error_str = str(dup_error).lower()
            if 'zero' in error_str or 'hardware' in error_str:
                print(f"[Duplicate] Hardware error detected (likely zero-gpu issue): {dup_error}")
                print(f"[Duplicate] Retrying with cpu-basic hardware...")
                
                # Retry with cpu-basic hardware
                duplicate_params["hardware"] = "cpu-basic"
                try:
                    duplicated_repo = duplicate_space(**duplicate_params)
                    print(f"[Duplicate] ✅ Successfully duplicated with cpu-basic hardware")
                except Exception as retry_error:
                    print(f"[Duplicate] Retry with cpu-basic also failed: {retry_error}")
                    raise retry_error
            else:
                # Not a hardware error, re-raise
                raise dup_error
        
        # Extract space URL
        space_url = f"https://huggingface.co/spaces/{to_space_id}"
        
        success_msg = f"✅ Space duplicated! View at: {space_url}"
        print(f"[Duplicate] {success_msg}")
        
        return True, success_msg, space_url
        
    except Exception as e:
        print(f"[Duplicate] Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, f"Failed to duplicate space: {str(e)}", None


def create_pull_request_on_space(
    repo_id: str,
    code: str,
    language: str,
    token: Optional[str] = None,
    pr_title: Optional[str] = None,
    pr_description: Optional[str] = None
) -> Tuple[bool, str, Optional[str]]:
    """
    Create a Pull Request on an existing HuggingFace Space with redesigned code
    
    Args:
        repo_id: Full repo ID (username/space-name)
        code: New code to propose
        language: Language/framework type
        token: HuggingFace API token
        pr_title: Title for the PR (default: "Redesign from AnyCoder")
        pr_description: Description for the PR
    
    Returns:
        Tuple of (success: bool, message: str, pr_url: Optional[str])
    """
    if not token:
        token = os.getenv("HF_TOKEN")
        if not token:
            return False, "No HuggingFace token provided", None
    
    try:
        api = HfApi(token=token)
        
        # Check if we can access the space first
        try:
            space_info = api.space_info(repo_id=repo_id, token=token)
            print(f"[PR] Space info: private={space_info.private if hasattr(space_info, 'private') else 'unknown'}")
            
            # Check if space is private
            if hasattr(space_info, 'private') and space_info.private:
                return False, "❌ Cannot create PR on private space. The space must be public to accept PRs from others.", None
        except Exception as info_error:
            print(f"[PR] Could not fetch space info: {info_error}")
            # Continue anyway - maybe we can still create the PR
        
        # Default PR title and description
        if not pr_title:
            pr_title = "🎨 Redesign from AnyCoder"
        
        if not pr_description:
            pr_description = """This Pull Request contains a redesigned version of the app with:

- ✨ Modern, mobile-friendly design
- 🎯 Minimal, clean components
- 📱 Responsive layout
- 🚀 Improved user experience

Generated by [AnyCoder](https://huggingface.co/spaces/akhaliq/anycoder)"""
        
        # Create temporary directory for files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Parse code based on language
            if language == "transformers.js":
                try:
                    files = parse_transformers_js_output(code)
                    print(f"[PR] Parsed transformers.js files: {list(files.keys())}")
                    
                    # Write transformers.js files
                    for filename, content in files.items():
                        file_path = temp_path / filename
                        if filename == "requirements.txt":
                            content = enforce_critical_versions(content)
                        file_path.write_text(content, encoding='utf-8')
                        
                except Exception as e:
                    print(f"[PR] Error parsing transformers.js: {e}")
                    return False, f"Error parsing transformers.js output: {str(e)}", None
                
            elif language == "html":
                html_code = parse_html_code(code)
                (temp_path / "index.html").write_text(html_code, encoding='utf-8')
                
            elif language == "comfyui":
                html_code = prettify_comfyui_json_for_html(code)
                (temp_path / "index.html").write_text(html_code, encoding='utf-8')
                
            elif language in ["gradio", "streamlit", "react"]:
                files = parse_multi_file_python_output(code)
                
                # Fallback if no files parsed
                if not files:
                    print(f"[PR] No file markers found, using entire code as main file")
                    cleaned_code = remove_code_block(code)
                    if language == "streamlit":
                        files["streamlit_app.py"] = cleaned_code
                    elif language == "react":
                        files["app.tsx"] = cleaned_code
                    else:
                        files["app.py"] = cleaned_code
                
                # For Gradio PRs, only include .py files (preserve existing requirements.txt, etc.)
                # For redesigns, ONLY include app.py to avoid modifying helper files
                if language == "gradio":
                    print(f"[PR] Gradio app - filtering to only .py files")
                    py_files = {fname: content for fname, content in files.items() if fname.endswith('.py')}
                    if not py_files:
                        print(f"[PR] Warning: No .py files found in parsed output")
                        return False, "No Python files found in generated code for Gradio PR", None
                    
                    # Check if this is a redesign (pr_title contains "Redesign")
                    is_redesign = "redesign" in pr_title.lower() if pr_title else False
                    
                    if is_redesign:
                        print(f"[PR] Redesign PR detected - filtering to ONLY app.py")
                        if 'app.py' not in py_files:
                            print(f"[PR] Warning: No app.py found in redesign output")
                            return False, "No app.py found in redesign output for Gradio PR", None
                        files = {'app.py': py_files['app.py']}
                        print(f"[PR] Will only update app.py ({len(py_files['app.py'])} chars)")
                    else:
                        files = py_files
                        print(f"[PR] Will update {len(files)} Python file(s): {list(files.keys())}")
                
                # Write files (create subdirectories if needed)
                for filename, content in files.items():
                    file_path = temp_path / filename
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    if filename == "requirements.txt":
                        content = enforce_critical_versions(content)
                    file_path.write_text(content, encoding='utf-8')
                
                # Skip requirements.txt generation for Gradio PRs (preserve existing)
                # For Streamlit, generate requirements.txt if missing
                if language in ["streamlit", "daggr"] and "requirements.txt" not in files:
                    main_app = files.get('streamlit_app.py') or files.get('app.py', '')
                    if main_app:
                        print(f"[PR] Generating requirements.txt from imports")
                        import_statements = extract_import_statements(main_app)
                        requirements_content = generate_requirements_txt_with_llm(import_statements)
                        (temp_path / "requirements.txt").write_text(requirements_content, encoding='utf-8')
            
            else:
                # Default: treat as code file
                files = parse_multi_file_python_output(code)
                if not files:
                    cleaned_code = remove_code_block(code)
                    files['app.py'] = cleaned_code
                
                for filename, content in files.items():
                    file_path = temp_path / filename
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(content, encoding='utf-8')
            
            # Create PR with files using create_commit (recommended approach)
            # This creates the PR and uploads files in one API call
            try:
                print(f"[PR] Creating pull request with files on {repo_id}")
                
                # Prepare operations for all files
                from huggingface_hub import CommitOperationAdd
                operations = []
                
                for file_path in temp_path.rglob('*'):
                    if file_path.is_file():
                        rel_path = file_path.relative_to(temp_path)
                        operations.append(
                            CommitOperationAdd(
                                path_in_repo=str(rel_path),
                                path_or_fileobj=str(file_path)
                            )
                        )
                
                print(f"[PR] Prepared {len(operations)} file operations")
                print(f"[PR] Token being used (first 20 chars): {token[:20] if token else 'None'}...")
                
                # Create commit with PR (pass token explicitly)
                commit_info = api.create_commit(
                    repo_id=repo_id,
                    repo_type="space",
                    operations=operations,
                    commit_message=pr_title,
                    commit_description=pr_description,
                    create_pr=True,  # This creates a PR with the changes
                    token=token,  # Explicitly pass token
                )
                
                # Extract PR URL
                pr_url = commit_info.pr_url if hasattr(commit_info, 'pr_url') else None
                pr_num = commit_info.pr_num if hasattr(commit_info, 'pr_num') else None
                
                if not pr_url and pr_num:
                    pr_url = f"https://huggingface.co/spaces/{repo_id}/discussions/{pr_num}"
                elif not pr_url:
                    pr_url = f"https://huggingface.co/spaces/{repo_id}/discussions"
                
                print(f"[PR] Created PR: {pr_url}")
                success_msg = f"✅ Pull Request created! View at: {pr_url}"
                
                return True, success_msg, pr_url
                
            except Exception as e:
                error_msg = str(e)
                print(f"[PR] Error creating pull request: {error_msg}")
                import traceback
                traceback.print_exc()
                
                # Provide helpful error message based on the error type
                if "403" in error_msg or "Forbidden" in error_msg or "Authorization" in error_msg:
                    user_msg = (
                        "❌ Cannot create Pull Request: Permission denied.\n\n"
                        "**Possible reasons:**\n"
                        "- The space owner hasn't enabled Pull Requests\n"
                        "- You don't have write access to this space\n"
                        "- Spaces have stricter PR permissions than models/datasets\n\n"
                        "**What you can do:**\n"
                        "✅ Use the 'Redesign' button WITHOUT checking 'Create PR' - this will:\n"
                        "   1. Duplicate the space to your account\n"
                        "   2. Apply the redesign to your copy\n"
                        "   3. You'll own the new space!\n\n"
                        "Or contact the space owner to enable Pull Requests."
                    )
                else:
                    user_msg = f"Failed to create pull request: {error_msg}"
                
                return False, user_msg, None
            
    except Exception as e:
        print(f"[PR] Top-level exception: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, f"Pull request error: {str(e)}", None

