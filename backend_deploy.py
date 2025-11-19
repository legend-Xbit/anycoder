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
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from huggingface_hub import HfApi


def parse_html_code(code: str) -> str:
    """Extract HTML code from various formats"""
    code = code.strip()
    
    # If already clean HTML, return as-is
    if code.startswith('<!DOCTYPE') or code.startswith('<html'):
        return code
    
    # Try to extract from code blocks
    if '```html' in code:
        match = re.search(r'```html\s*(.*?)\s*```', code, re.DOTALL)
        if match:
            return match.group(1).strip()
    
    if '```' in code:
        match = re.search(r'```\s*(.*?)\s*```', code, re.DOTALL)
        if match:
            return match.group(1).strip()
    
    return code


def parse_transformers_js_output(code: str) -> Dict[str, str]:
    """Parse transformers.js output into separate files"""
    files = {}
    
    # First try: Pattern to match === filename === sections
    pattern = r'===\s*(\S+\.(?:html|js|css))\s*===\s*(.*?)(?====|$)'
    matches = re.finditer(pattern, code, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        filename = match.group(1).strip()
        content = match.group(2).strip()
        
        # Clean up code blocks if present
        content = re.sub(r'^```\w*\s*', '', content, flags=re.MULTILINE)
        content = re.sub(r'```\s*$', '', content, flags=re.MULTILINE)
        
        files[filename] = content
    
    # Fallback: Try to extract from markdown code blocks if === format not found
    if not files:
        print("[Deploy] === format not found, trying markdown code blocks fallback")
        
        # Try to find ```html, ```javascript, ```css blocks
        html_match = re.search(r'```html\s*(.*?)```', code, re.DOTALL | re.IGNORECASE)
        js_match = re.search(r'```javascript\s*(.*?)```', code, re.DOTALL | re.IGNORECASE)
        css_match = re.search(r'```css\s*(.*?)```', code, re.DOTALL | re.IGNORECASE)
        
        if html_match:
            content = html_match.group(1).strip()
            # Remove comment lines like "<!-- index.html content here -->"
            content = re.sub(r'<!--\s*index\.html.*?-->\s*', '', content, flags=re.IGNORECASE)
            files['index.html'] = content
            
        if js_match:
            content = js_match.group(1).strip()
            # Remove comment lines like "// index.js content here"
            content = re.sub(r'//\s*index\.js.*?\n', '', content, flags=re.IGNORECASE)
            files['index.js'] = content
            
        if css_match:
            content = css_match.group(1).strip()
            # Remove comment lines like "/* style.css content here */"
            content = re.sub(r'/\*\s*style\.css.*?\*/', '', content, flags=re.IGNORECASE)
            files['style.css'] = content
    
    # Last resort: try to extract as single HTML file
    if not files:
        html_content = parse_html_code(code)
        if html_content:
            files['index.html'] = html_content
    
    return files


def parse_python_requirements(code: str) -> Optional[str]:
    """Extract requirements.txt content from code if present"""
    # Look for requirements.txt section
    req_pattern = r'===\s*requirements\.txt\s*===\s*(.*?)(?====|$)'
    match = re.search(req_pattern, code, re.DOTALL | re.IGNORECASE)
    
    if match:
        requirements = match.group(1).strip()
        # Clean up code blocks
        requirements = re.sub(r'^```\w*\s*', '', requirements, flags=re.MULTILINE)
        requirements = re.sub(r'```\s*$', '', requirements, flags=re.MULTILINE)
        return requirements
    
    return None


def parse_multi_file_python_output(code: str) -> Dict[str, str]:
    """Parse multi-file Python output (e.g., Gradio, Streamlit)"""
    files = {}
    
    # Pattern to match file sections
    pattern = r'===\s*(\S+\.(?:py|txt))\s*===\s*(.*?)(?====|$)'
    matches = re.finditer(pattern, code, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        filename = match.group(1).strip()
        content = match.group(2).strip()
        
        # Clean up code blocks if present
        content = re.sub(r'^```\w*\s*', '', content, flags=re.MULTILINE)
        content = re.sub(r'```\s*$', '', content, flags=re.MULTILINE)
        
        files[filename] = content
    
    # If no files were parsed, treat as single app.py
    if not files:
        # Clean up code blocks
        clean_code = re.sub(r'^```\w*\s*', '', code, flags=re.MULTILINE)
        clean_code = re.sub(r'```\s*$', '', clean_code, flags=re.MULTILINE)
        files['app.py'] = clean_code.strip()
    
    return files


def is_streamlit_code(code: str) -> bool:
    """Check if code is Streamlit"""
    return 'import streamlit' in code or 'streamlit.run' in code


def is_gradio_code(code: str) -> bool:
    """Check if code is Gradio"""
    return 'import gradio' in code or 'gr.' in code


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
    elif language == "gradio" or is_gradio_code(code):
        return "gradio"
    else:
        return "gradio"  # Default


def add_anycoder_tag_to_readme(api, repo_id: str, app_port: Optional[int] = None) -> None:
    """
    Download existing README, add anycoder tag and app_port if needed, and upload back.
    Preserves all existing README content and frontmatter.
    
    Args:
        api: HuggingFace API client
        repo_id: Repository ID (username/space-name)
        app_port: Optional port number to set for Docker spaces (e.g., 7860)
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


def deploy_to_huggingface_space(
    code: str,
    language: str,
    space_name: Optional[str] = None,
    token: Optional[str] = None,
    username: Optional[str] = None,
    description: Optional[str] = None,
    private: bool = False,
    existing_repo_id: Optional[str] = None,
    commit_message: Optional[str] = None
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
    
    Returns:
        Tuple of (success: bool, message: str, space_url: Optional[str])
    """
    if not token:
        token = os.getenv("HF_TOKEN")
        if not token:
            return False, "No HuggingFace token provided", None
    
    try:
        api = HfApi(token=token)
        
        # Determine if this is an update or new deployment
        is_update = existing_repo_id is not None
        
        if is_update:
            # Use existing repo
            repo_id = existing_repo_id
            space_name = existing_repo_id.split('/')[-1]
            username = existing_repo_id.split('/')[0] if '/' in existing_repo_id else username
        else:
            # Get username if not provided
            if not username:
                try:
                    user_info = api.whoami()
                    username = user_info.get("name") or user_info.get("preferred_username") or "user"
                except Exception as e:
                    return False, f"Failed to get user info: {str(e)}", None
            
            # Generate space name if not provided
            if not space_name:
                space_name = f"anycoder-{uuid.uuid4().hex[:8]}"
            
            # Clean space name (no spaces, lowercase, alphanumeric + hyphens)
            space_name = re.sub(r'[^a-z0-9-]', '-', space_name.lower())
            space_name = re.sub(r'-+', '-', space_name).strip('-')
            
            repo_id = f"{username}/{space_name}"
        
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
                    
                    # Validate all three files are present
                    missing_files = []
                    if not files.get('index.html'):
                        missing_files.append('index.html')
                    if not files.get('index.js'):
                        missing_files.append('index.js')
                    if not files.get('style.css'):
                        missing_files.append('style.css')
                    
                    if missing_files:
                        error_msg = f"Missing required files: {', '.join(missing_files)}. "
                        error_msg += f"Found only: {', '.join(files.keys()) if files else 'no files'}. "
                        error_msg += "Transformers.js apps require all three files with === filename === markers. Please regenerate the code."
                        print(f"[Deploy] {error_msg}")
                        return False, error_msg, None
                    
                    # Validate files have content
                    empty_files = [name for name, content in files.items() if not content or not content.strip()]
                    if empty_files:
                        error_msg = f"Empty files detected: {', '.join(empty_files)}. Please regenerate the code with actual content."
                        print(f"[Deploy] {error_msg}")
                        return False, error_msg, None
                    
                    # Write transformers.js files
                    for filename, content in files.items():
                        print(f"[Deploy] Writing {filename} ({len(content)} chars)")
                        (temp_path / filename).write_text(content, encoding='utf-8')
                    
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
                # ComfyUI is JSON, wrap in HTML viewer
                (temp_path / "index.html").write_text(code, encoding='utf-8')
                
            elif language in ["gradio", "streamlit"]:
                files = parse_multi_file_python_output(code)
                
                # Write Python files (create subdirectories if needed)
                for filename, content in files.items():
                    file_path = temp_path / filename
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(content, encoding='utf-8')
                
                # Ensure requirements.txt exists
                if "requirements.txt" not in files:
                    if language == "gradio":
                        (temp_path / "requirements.txt").write_text("gradio>=4.0.0\n", encoding='utf-8')
                    elif language == "streamlit":
                        (temp_path / "requirements.txt").write_text("streamlit>=1.30.0\n", encoding='utf-8')
                
                # Create Dockerfile if needed
                if sdk == "docker":
                    if language == "streamlit":
                        dockerfile = create_dockerfile_for_streamlit(space_name)
                        (temp_path / "Dockerfile").write_text(dockerfile, encoding='utf-8')
                    app_port = 7860  # Set app_port for Docker spaces
                    use_individual_uploads = True  # Streamlit uses individual file uploads
                
            elif language == "react":
                # Parse React output to get all files (uses same multi-file format as Python)
                files = parse_multi_file_python_output(code)
                
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
                
                # Write files (create subdirectories if needed)
                for filename, content in files.items():
                    file_path = temp_path / filename
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(content, encoding='utf-8')
                
                if "requirements.txt" not in files:
                    (temp_path / "requirements.txt").write_text("gradio>=4.0.0\n", encoding='utf-8')
            
            # Don't create README - HuggingFace will auto-generate it
            # We'll add the anycoder tag after deployment
            
            # ALWAYS create/ensure repo exists (with exist_ok=True)
            # This works for both new spaces and updates!
            try:
                if language == "transformers.js" and not is_update:
                    # For NEW transformers.js spaces, try to duplicate the template
                    print(f"[Deploy] Creating new transformers.js space: {repo_id}")
                    try:
                        from huggingface_hub import duplicate_space
                        
                        # IMPORTANT: duplicate_space expects just the space name, not the full repo_id
                        # It will automatically prepend the username
                        print(f"[Deploy] Attempting to duplicate template space to: {space_name}")
                        result = duplicate_space(
                            from_id="static-templates/transformers.js",
                            to_id=space_name,  # Just the space name, not username/space-name
                            token=token,
                            exist_ok=True
                        )
                        print(f"[Deploy] Template duplication result: {result}")
                    except Exception as e:
                        # If template duplication fails, fall back to regular create
                        print(f"[Deploy] Template duplication failed, creating regular static space: {e}")
                        import traceback
                        traceback.print_exc()
                        api.create_repo(
                            repo_id=repo_id,
                            repo_type="space",
                            space_sdk=sdk,
                            private=private,
                            exist_ok=True  # Don't fail if exists
                        )
                else:
                    # For all other cases (new or update), ensure repo exists
                    print(f"[Deploy] Ensuring repo exists: {repo_id} (is_update={is_update})")
                    api.create_repo(
                        repo_id=repo_id,
                        repo_type="space",
                        space_sdk=sdk,
                        private=private if not is_update else None,  # Only set private for new repos
                        exist_ok=True  # Don't fail if repo already exists
                    )
            except Exception as e:
                return False, f"Failed to create/access space: {str(e)}", None
            
            # Upload files
            if not commit_message:
                commit_message = "Update from anycoder" if is_update else "Deploy from anycoder"
            
            try:
                if use_individual_uploads:
                    # For transformers.js, React, Streamlit: upload each file individually (matches original deploy.py)
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
                        
                        # Upload with retry logic (like original)
                        success = False
                        last_error = None
                        
                        for attempt in range(max_attempts):
                            try:
                                api.upload_file(
                                    path_or_fileobj=str(file_path),
                                    path_in_repo=filename,
                                    repo_id=repo_id,
                                    repo_type="space",
                                    commit_message=f"{commit_message} - {filename}"
                                )
                                success = True
                                print(f"[Deploy] Successfully uploaded {filename}")
                                break
                            except Exception as e:
                                last_error = e
                                if "403" in str(e) or "Forbidden" in str(e):
                                    return False, f"Permission denied uploading {filename}. Check your token has write access.", None
                                if attempt < max_attempts - 1:
                                    time.sleep(2)  # Wait before retry
                                    print(f"[Deploy] Retry {attempt + 1}/{max_attempts} for {filename}")
                        
                        if not success:
                            return False, f"Failed to upload {filename} after {max_attempts} attempts: {last_error}", None
                else:
                    # For other languages, use upload_folder
                    api.upload_folder(
                        folder_path=str(temp_path),
                        repo_id=repo_id,
                        repo_type="space",
                        commit_message=commit_message
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
                add_anycoder_tag_to_readme(api, repo_id, app_port)
            except Exception as e:
                # Don't fail deployment if README modification fails
                print(f"Warning: Could not add anycoder tag to README: {e}")
            
            space_url = f"https://huggingface.co/spaces/{repo_id}"
            action = "Updated" if is_update else "Deployed"
            return True, f"✅ {action} successfully to {repo_id}!", space_url
            
    except Exception as e:
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

