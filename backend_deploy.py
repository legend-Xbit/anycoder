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
    
    # Pattern to match file sections
    pattern = r'===\s*(\S+\.(?:html|js|css))\s*===\s*(.*?)(?====|$)'
    matches = re.finditer(pattern, code, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        filename = match.group(1).strip()
        content = match.group(2).strip()
        
        # Clean up code blocks if present
        content = re.sub(r'^```\w*\s*', '', content, flags=re.MULTILINE)
        content = re.sub(r'```\s*$', '', content, flags=re.MULTILINE)
        
        files[filename] = content
    
    # If no files were parsed, try to extract as single HTML file
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


def create_space_readme(space_name: str, sdk: str, description: str = None) -> str:
    """Create README.md for HuggingFace Space"""
    readme = f"""---
title: {space_name}
emoji: 🚀
colorFrom: blue
colorTo: purple
sdk: {sdk}
sdk_version: 4.44.1
app_file: app.py
pinned: false
"""
    
    if sdk == "docker":
        readme += "app_port: 7860\n"
    
    readme += "---\n\n"
    
    if description:
        readme += f"{description}\n\n"
    else:
        readme += f"# {space_name}\n\nBuilt with [anycoder](https://huggingface.co/spaces/akhaliq/anycoder)\n"
    
    return readme


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
    private: bool = False
) -> Tuple[bool, str, Optional[str]]:
    """
    Deploy code to HuggingFace Spaces
    
    Args:
        code: Generated code to deploy
        language: Target language/framework (html, gradio, streamlit, react, transformers.js, comfyui)
        space_name: Name for the space (auto-generated if None)
        token: HuggingFace API token
        username: HuggingFace username
        description: Space description
        private: Whether to make the space private
    
    Returns:
        Tuple of (success: bool, message: str, space_url: Optional[str])
    """
    if not token:
        token = os.getenv("HF_TOKEN")
        if not token:
            return False, "No HuggingFace token provided", None
    
    try:
        api = HfApi(token=token)
        
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
            if language == "transformers.js":
                files = parse_transformers_js_output(code)
                
                # Write transformers.js files
                for filename, content in files.items():
                    (temp_path / filename).write_text(content, encoding='utf-8')
                
                # Create README
                readme = create_space_readme(space_name, "static", description)
                (temp_path / "README.md").write_text(readme, encoding='utf-8')
                
            elif language == "html":
                html_code = parse_html_code(code)
                (temp_path / "index.html").write_text(html_code, encoding='utf-8')
                
                # Create README
                readme = create_space_readme(space_name, "static", description)
                (temp_path / "README.md").write_text(readme, encoding='utf-8')
                
            elif language == "comfyui":
                # ComfyUI is JSON, wrap in HTML viewer
                (temp_path / "index.html").write_text(code, encoding='utf-8')
                
                # Create README
                readme = create_space_readme(space_name, "static", description)
                (temp_path / "README.md").write_text(readme, encoding='utf-8')
                
            elif language in ["gradio", "streamlit"]:
                files = parse_multi_file_python_output(code)
                
                # Write Python files
                for filename, content in files.items():
                    (temp_path / filename).write_text(content, encoding='utf-8')
                
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
                
                # Create README
                readme = create_space_readme(space_name, sdk, description)
                (temp_path / "README.md").write_text(readme, encoding='utf-8')
                
            elif language == "react":
                # For React, we'd need package.json and other files
                # This is more complex, so for now just create a placeholder
                files = parse_multi_file_python_output(code)
                
                for filename, content in files.items():
                    (temp_path / filename).write_text(content, encoding='utf-8')
                
                # Create Dockerfile
                dockerfile = create_dockerfile_for_react(space_name)
                (temp_path / "Dockerfile").write_text(dockerfile, encoding='utf-8')
                
                # Create README
                readme = create_space_readme(space_name, "docker", description)
                (temp_path / "README.md").write_text(readme, encoding='utf-8')
            
            else:
                # Default: treat as Gradio app
                files = parse_multi_file_python_output(code)
                
                for filename, content in files.items():
                    (temp_path / filename).write_text(content, encoding='utf-8')
                
                if "requirements.txt" not in files:
                    (temp_path / "requirements.txt").write_text("gradio>=4.0.0\n", encoding='utf-8')
                
                # Create README
                readme = create_space_readme(space_name, "gradio", description)
                (temp_path / "README.md").write_text(readme, encoding='utf-8')
            
            # Create the space
            try:
                api.create_repo(
                    repo_id=repo_id,
                    repo_type="space",
                    space_sdk=sdk,
                    private=private,
                    exist_ok=False
                )
            except Exception as e:
                if "already exists" in str(e).lower():
                    # Space exists, we'll update it
                    pass
                else:
                    return False, f"Failed to create space: {str(e)}", None
            
            # Upload all files
            try:
                api.upload_folder(
                    folder_path=str(temp_path),
                    repo_id=repo_id,
                    repo_type="space",
                    commit_message="Deploy from anycoder"
                )
            except Exception as e:
                return False, f"Failed to upload files: {str(e)}", None
            
            space_url = f"https://huggingface.co/spaces/{repo_id}"
            return True, f"✅ Successfully deployed to {repo_id}!", space_url
            
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

