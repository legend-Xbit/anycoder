"""
Backend parser utilities for AnyCoder.
Handles parsing of various code formats including transformers.js, Python multi-file outputs, and more.
"""
import re
import json
import ast
from typing import Dict, Optional
from backend_models import get_inference_client, get_real_model_id


def parse_transformers_js_output(code: str) -> Dict[str, str]:
    """Parse transformers.js output into separate files (index.html, index.js, style.css)
    
    Uses comprehensive parsing patterns to handle various LLM output formats.
    Updated to use transformers.js v3.8.0 CDN.
    """
    print(f"[Parser] Received code length: {len(code)} characters")
    print(f"[Parser] First 200 chars: {code[:200]}")
    
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
        # Use regex to extract sections - support alternative filenames
        # Stop at next === marker, or common end markers
        # More aggressive: stop at blank line followed by explanatory text patterns
        html_fallback = re.search(r'===\s*index\.html\s*===\s*\n([\s\S]+?)(?=\n===|\n\s*---|\n\n(?:This |✨|🎨|🚀|\*\*Key Features|\*\*Design)|$)', code, re.IGNORECASE)
        
        # Try both index.js and app.js  
        js_fallback = re.search(r'===\s*(?:index\.js|app\.js)\s*===\s*\n([\s\S]+?)(?=\n===|\n\s*---|\n\n(?:This |✨|🎨|🚀|\*\*Key Features|\*\*Design)|$)', code, re.IGNORECASE)
        
        # Try both style.css and styles.css
        css_fallback = re.search(r'===\s*(?:style\.css|styles\.css)\s*===\s*\n([\s\S]+?)(?=\n===|\n\s*---|\n\n(?:This |✨|🎨|🚀|\*\*Key Features|\*\*Design)|$)', code, re.IGNORECASE)
        
        print(f"[Parser] Fallback extraction - HTML found: {bool(html_fallback)}, JS found: {bool(js_fallback)}, CSS found: {bool(css_fallback)}")
        
        if html_fallback:
            files['index.html'] = html_fallback.group(1).strip()
        if js_fallback:
            js_content = js_fallback.group(1).strip()
            # Fix common JavaScript syntax issues from LLM output
            # Fix line breaks in string literals (common LLM mistake)
            js_content = re.sub(r'"\s*\n\s*([^"])', r'" + "\1', js_content)  # Fix broken strings
            files['index.js'] = js_content
        if css_fallback:
            css_content = css_fallback.group(1).strip()
            files['style.css'] = css_content
            
            # Also normalize HTML to reference style.css (singular)
            if files['index.html'] and 'styles.css' in files['index.html']:
                print("[Parser] Normalizing styles.css reference to style.css in HTML")
                files['index.html'] = files['index.html'].replace('href="styles.css"', 'href="style.css"')
                files['index.html'] = files['index.html'].replace("href='styles.css'", "href='style.css'")
    
    # Additional fallback: extract from numbered sections or file headers
    if not (files['index.html'] and files['index.js'] and files['style.css']):
        # Try patterns like "1. index.html:" or "**index.html**"
        patterns = [
            (r'(?:^\d+\.\s*|^##\s*|^\*\*\s*)index\.html(?:\s*:|\*\*:?)\s*\n([\s\S]+?)(?=\n(?:\d+\.|##|\*\*|===)|$)', 'index.html'),
            (r'(?:^\d+\.\s*|^##\s*|^\*\*\s*)(?:index\.js|app\.js)(?:\s*:|\*\*:?)\s*\n([\s\S]+?)(?=\n(?:\d+\.|##|\*\*|===)|$)', 'index.js'),
            (r'(?:^\d+\.\s*|^##\s*|^\*\*\s*)(?:style\.css|styles\.css)(?:\s*:|\*\*:?)\s*\n([\s\S]+?)(?=\n(?:\d+\.|##|\*\*|===)|$)', 'style.css')
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
    
    # Normalize filename references in HTML
    if files['index.html'] and files['style.css']:
        if 'styles.css' in files['index.html']:
            print("[Parser] Normalizing styles.css reference to style.css in HTML")
            files['index.html'] = files['index.html'].replace('href="styles.css"', 'href="style.css"')
            files['index.html'] = files['index.html'].replace("href='styles.css'", "href='style.css'")
    
    if files['index.html'] and files['index.js']:
        if 'app.js' in files['index.html']:
            print("[Parser] Normalizing app.js reference to index.js in HTML")
            files['index.html'] = files['index.html'].replace('src="app.js"', 'src="index.js"')
            files['index.html'] = files['index.html'].replace("src='app.js'", "src='index.js'")
    
    # Normalize transformers.js imports to use v3.8.0 CDN
    cdn_url = "https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.8.0"
    
    for file_key in ['index.html', 'index.js']:
        if files[file_key]:
            content = files[file_key]
            # Update import statements to use latest CDN
            content = re.sub(
                r"from\s+['\"]https://cdn.jsdelivr.net/npm/@huggingface/transformers@[^'\"]+['\"]",
                f"from '{cdn_url}'",
                content
            )
            content = re.sub(
                r"from\s+['\"]https://cdn.jsdelivr.net/npm/@xenova/transformers@[^'\"]+['\"]",
                f"from '{cdn_url}'",
                content
            )
            files[file_key] = content
    
    return files


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
    
    # Pattern to match file sections like === filename.ext ===
    pattern = r'===\s*(\S+\.\w+)\s*===\s*(.*?)(?=\n\s*===\s*\S+\.\w+\s*===|$)'
    matches = re.finditer(pattern, code, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        filename = match.group(1).strip()
        content = match.group(2).strip()
        
        # Clean up code blocks
        content = re.sub(r'^```\w*\s*', '', content, flags=re.MULTILINE)
        content = re.sub(r'```\s*$', '', content, flags=re.MULTILINE)
        
        if filename == "requirements.txt":
            content = enforce_critical_versions(content)
        files[filename] = content
    
    return files


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


def parse_multipage_html_output(text: str) -> Dict[str, str]:
    """Parse multi-page HTML output formatted as repeated "=== filename ===" sections.

    Returns a mapping of filename → file content. Supports nested paths like assets/css/styles.css.
    If HTML content appears before the first === marker, it's treated as index.html.
    """
    if not text:
        return {}
    # First, strip any markdown fences
    cleaned = remove_code_block(text)
    files: Dict[str, str] = {}
    
    # Check if there's content before the first === marker
    first_marker_match = re.search(r"^===\s*([^=\n]+?)\s*===", cleaned, re.MULTILINE)
    if first_marker_match:
        # There's content before the first marker
        first_marker_pos = first_marker_match.start()
        if first_marker_pos > 0:
            leading_content = cleaned[:first_marker_pos].strip()
            # Check if it looks like HTML content
            if leading_content and ('<!DOCTYPE' in leading_content or '<html' in leading_content or leading_content.startswith('<')):
                files['index.html'] = leading_content
        
        # Now parse the rest with === markers
        remaining_text = cleaned[first_marker_pos:] if first_marker_pos > 0 else cleaned
        pattern = re.compile(r"^===\s*([^=\n]+?)\s*===\s*\n([\s\S]*?)(?=\n===\s*[^=\n]+?\s*===|\Z)", re.MULTILINE)
        for m in pattern.finditer(remaining_text):
            name = m.group(1).strip()
            content = m.group(2).strip()
            # Remove accidental trailing fences if present
            content = re.sub(r"^```\w*\s*\n|\n```\s*$", "", content)
            files[name] = content
    else:
        # No === markers found, try standard pattern matching
        pattern = re.compile(r"^===\s*([^=\n]+?)\s*===\s*\n([\s\S]*?)(?=\n===\s*[^=\n]+?\s*===|\Z)", re.MULTILINE)
        for m in pattern.finditer(cleaned):
            name = m.group(1).strip()
            content = m.group(2).strip()
            # Remove accidental trailing fences if present
            content = re.sub(r"^```\w*\s*\n|\n```\s*$", "", content)
            files[name] = content
    
    return files


def parse_react_output(text: str) -> Dict[str, str]:
    """Parse React/Next.js output to extract individual files.

    Supports multi-file sections using === filename === sections.
    """
    if not text:
        return {}

    # Use the generic multipage parser
    try:
        files = parse_multipage_html_output(text) or {}
    except Exception:
        files = {}

    return files if isinstance(files, dict) and files else {}


def enforce_critical_versions(requirements_content: str) -> str:
    """Ensure critical packages like daggr and gradio have minimum required versions"""
    if 'daggr' in requirements_content:
        # Check if version is already specified
        if 'daggr>=' not in requirements_content and 'daggr==' not in requirements_content:
            # Replace plain 'daggr' with pinned version, preserving comments
            requirements_content = re.sub(r'^daggr\s*(?=[#\n]|$)', 'daggr>=0.5.4', requirements_content, flags=re.MULTILINE)
    
    if 'gradio' in requirements_content:
        if 'gradio>=' not in requirements_content and 'gradio==' not in requirements_content:
            # Replace plain 'gradio' with pinned version, preserving comments
            requirements_content = re.sub(r'^gradio\s*(?=[#\n]|$)', 'gradio>=6.0.2', requirements_content, flags=re.MULTILINE)
            
    return requirements_content


def generate_requirements_txt_with_llm(import_statements):
    """Generate requirements.txt content using LLM based on import statements."""
    if not import_statements:
        return "# No additional dependencies required\n"
    
    # Use a lightweight model for this task
    try:
        client = get_inference_client("zai-org/GLM-4.7", "auto")
        actual_model_id = get_real_model_id("zai-org/GLM-4.7")
        
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
- IMPORTANT: For daggr, ALWAYS use: daggr>=0.5.4
- Examples of comprehensive dependencies:
  * diffusers often needs: git+https://github.com/huggingface/transformers, sentencepiece, accelerate, torch, tokenizers
  * transformers often needs: accelerate, torch, tokenizers, datasets
  * gradio often needs: gradio>=6.0, requests, Pillow for image handling (ALWAYS use gradio>=6.0)
  * pandas often needs: numpy, openpyxl for Excel files
  * matplotlib often needs: numpy, pillow for image saving
  * sklearn often needs: numpy, scipy, joblib
  * streamlit often needs: pandas, numpy, requests
  * opencv-python often needs: numpy, pillow
  * fastapi often needs: uvicorn, pydantic
  * daggr often needs: daggr>=0.5.4, gradio>=6.0, pydub
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
        
        requirements_content = enforce_critical_versions(requirements_content)
        
        # Ensure it ends with a newline
        if requirements_content and not requirements_content.endswith('\n'):
            requirements_content += '\n'
            
        return requirements_content if requirements_content else "# No additional dependencies required\n"
        
    except Exception as e:
        # Fallback: simple extraction with basic mapping
        print(f"[Parser] Warning: LLM requirements generation failed: {e}, using fallback")
        dependencies = set()
        special_cases = {
            'PIL': 'Pillow', 
            'sklearn': 'scikit-learn',
            'skimage': 'scikit-image',
            'bs4': 'beautifulsoup4',
            'daggr': 'daggr>=0.5.4',
            'gradio': 'gradio>=6.0.2'
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

