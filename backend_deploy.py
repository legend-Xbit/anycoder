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
    strip_tool_call_markers,
    remove_code_block,
    extract_import_statements,
    generate_requirements_txt_with_llm
)


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


def parse_transformers_js_output(code: str) -> Dict[str, str]:
    """Parse transformers.js output into separate files (index.html, index.js, style.css)
    
    Uses comprehensive parsing patterns to handle various LLM output formats.
    """
    files = {
        'index.html': '',
        'index.js': '',
        'style.css': ''
    }
    
    # Multiple patterns to match the three code blocks with different variations
    html_patterns = [
        r'```html\s*\n([\s\S]*?)(?:```|\Z)',
        r'```htm\s*\n([\s\S]*?)(?:```|\Z)',
        r'```\s*(?:index\.html|html)\s*\n([\s\S]*?)(?:```|\Z)'
    ]
    
    js_patterns = [
        r'```javascript\s*\n([\s\S]*?)(?:```|\Z)',
        r'```js\s*\n([\s\S]*?)(?:```|\Z)',
        r'```\s*(?:index\.js|javascript|js)\s*\n([\s\S]*?)(?:```|\Z)'
    ]
    
    css_patterns = [
        r'```css\s*\n([\s\S]*?)(?:```|\Z)',
        r'```\s*(?:style\.css|css)\s*\n([\s\S]*?)(?:```|\Z)'
    ]
    
    # Extract HTML content
    for pattern in html_patterns:
        html_match = re.search(pattern, code, re.IGNORECASE)
        if html_match:
            files['index.html'] = html_match.group(1).strip()
            break
    
    # Extract JavaScript content
    for pattern in js_patterns:
        js_match = re.search(pattern, code, re.IGNORECASE)
        if js_match:
            files['index.js'] = js_match.group(1).strip()
            break
    
    # Extract CSS content
    for pattern in css_patterns:
        css_match = re.search(pattern, code, re.IGNORECASE)
        if css_match:
            files['style.css'] = css_match.group(1).strip()
            break
    
    # Fallback: support === index.html === format if any file is missing
    if not (files['index.html'] and files['index.js'] and files['style.css']):
        # Use regex to extract sections
        html_fallback = re.search(r'===\s*index\.html\s*===\s*\n([\s\S]+?)(?=\n===|$)', code, re.IGNORECASE)
        js_fallback = re.search(r'===\s*index\.js\s*===\s*\n([\s\S]+?)(?=\n===|$)', code, re.IGNORECASE)
        css_fallback = re.search(r'===\s*style\.css\s*===\s*\n([\s\S]+?)(?=\n===|$)', code, re.IGNORECASE)
        
        if html_fallback:
            files['index.html'] = html_fallback.group(1).strip()
        if js_fallback:
            files['index.js'] = js_fallback.group(1).strip()
        if css_fallback:
            files['style.css'] = css_fallback.group(1).strip()
    
    # Additional fallback: extract from numbered sections or file headers
    if not (files['index.html'] and files['index.js'] and files['style.css']):
        # Try patterns like "1. index.html:" or "**index.html**"
        patterns = [
            (r'(?:^\d+\.\s*|^##\s*|^\*\*\s*)index\.html(?:\s*:|\*\*:?)\s*\n([\s\S]+?)(?=\n(?:\d+\.|##|\*\*|===)|$)', 'index.html'),
            (r'(?:^\d+\.\s*|^##\s*|^\*\*\s*)index\.js(?:\s*:|\*\*:?)\s*\n([\s\S]+?)(?=\n(?:\d+\.|##|\*\*|===)|$)', 'index.js'),
            (r'(?:^\d+\.\s*|^##\s*|^\*\*\s*)style\.css(?:\s*:|\*\*:?)\s*\n([\s\S]+?)(?=\n(?:\d+\.|##|\*\*|===)|$)', 'style.css')
        ]
        
        for pattern, file_key in patterns:
            if not files[file_key]:
                match = re.search(pattern, code, re.IGNORECASE | re.MULTILINE)
                if match:
                    # Clean up the content by removing any code block markers
                    content = match.group(1).strip()
                    content = re.sub(r'^```\w*\s*\n', '', content)
                    content = re.sub(r'\n```\s*$', '', content)
                    files[file_key] = content.strip()
    
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


def strip_tool_call_markers(text):
    """Remove TOOL_CALL markers and thinking tags that some LLMs add to their output."""
    if not text:
        return text
    # Remove [TOOL_CALL] and [/TOOL_CALL] markers
    text = re.sub(r'\[/?TOOL_CALL\]', '', text, flags=re.IGNORECASE)
    # Remove <think> and </think> tags and their content
    text = re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.IGNORECASE)
    # Remove any remaining unclosed <think> tags at the start
    text = re.sub(r'^<think>[\s\S]*?(?=\n|$)', '', text, flags=re.IGNORECASE | re.MULTILINE)
    # Remove any remaining </think> tags
    text = re.sub(r'</think>', '', text, flags=re.IGNORECASE)
    # Remove standalone }} that appears with tool calls
    # Only remove if it's on its own line or at the end
    text = re.sub(r'^\s*\}\}\s*$', '', text, flags=re.MULTILINE)
    return text.strip()


def remove_code_block(text):
    """Remove code block markers from text."""
    # First strip any tool call markers
    text = strip_tool_call_markers(text)
    
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
            # Remove a leading language marker line (e.g., 'python') if present
            if extracted.split('\n', 1)[0].strip().lower() in ['python', 'html', 'css', 'javascript', 'json', 'c', 'cpp', 'markdown', 'latex', 'jinja2', 'typescript', 'yaml', 'dockerfile', 'shell', 'r', 'sql']:
                return extracted.split('\n', 1)[1] if '\n' in extracted else ''
            return extracted
    # If no code block is found, return as-is
    return text.strip()


def extract_import_statements(code):
    """Extract import statements from generated code."""
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
        actual_model_id = get_real_model_id("zai-org/GLM-4.6")
        
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
            model=actual_model_id,
            messages=messages,
            max_tokens=1024,
            temperature=0.1
        )
        
        requirements_content = response.choices[0].message.content.strip()
        
        # Clean up the response in case it includes extra formatting
        if '```' in requirements_content:
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
        print(f"[Deploy] Warning: LLM requirements generation failed: {e}, using fallback")
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
                
            elif language in ["gradio", "streamlit"]:
                files = parse_multi_file_python_output(code)
                
                # Write Python files (create subdirectories if needed)
                for filename, content in files.items():
                    file_path = temp_path / filename
                    file_path.parent.mkdir(parents=True, exist_ok=True)
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
                                # Create a NEW temp file for this upload (key difference from old approach)
                                print(f"[Deploy] Creating temp file for {file_name} with {len(file_content)} chars")
                                with tempfile.NamedTemporaryFile("w", suffix=f".{file_name.split('.')[-1]}", delete=False, encoding='utf-8') as f:
                                    f.write(file_content)
                                    f.flush()  # Ensure all content is written to disk before closing
                                    temp_file_path = f.name
                                # File is now closed and flushed, safe to upload
                                
                                # Verify temp file size before upload
                                import os as _os
                                temp_size = _os.path.getsize(temp_file_path)
                                print(f"[Deploy] Temp file {file_name} size on disk: {temp_size} bytes (expected ~{len(file_content)} chars)")
                                
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
                add_anycoder_tag_to_readme(api, repo_id, app_port)
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
            return True, f"✅ {action} successfully to {repo_id}!", space_url
            
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

