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
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import html2text
import json
import time
import webbrowser
import urllib.parse

import gradio as gr
from huggingface_hub import InferenceClient
from tavily import TavilyClient
from huggingface_hub import HfApi
import tempfile

# Gradio supported languages for syntax highlighting
GRADIO_SUPPORTED_LANGUAGES = [
    "python", "c", "cpp", "markdown", "latex", "json", "html", "css", "javascript", "jinja2", "typescript", "yaml", "dockerfile", "shell", "r", "sql", "sql-msSQL", "sql-mySQL", "sql-mariaDB", "sql-sqlite", "sql-cassandra", "sql-plSQL", "sql-hive", "sql-pgSQL", "sql-gql", "sql-gpSQL", "sql-sparkSQL", "sql-esper", None
]

def get_gradio_language(language):
    return language if language in GRADIO_SUPPORTED_LANGUAGES else None

# Search/Replace Constants
SEARCH_START = "<<<<<<< SEARCH"
DIVIDER = "======="
REPLACE_END = ">>>>>>> REPLACE"

# Configuration
HTML_SYSTEM_PROMPT = """ONLY USE HTML, CSS AND JAVASCRIPT. If you want to use ICON make sure to import the library first. Try to create the best UI possible by using only HTML, CSS and JAVASCRIPT. MAKE IT RESPONSIVE USING MODERN CSS. Use as much as you can modern CSS for the styling, if you can't do something with modern CSS, then use custom CSS. Also, try to elaborate as much as you can, to create something unique. ALWAYS GIVE THE RESPONSE INTO A SINGLE HTML FILE

For website redesign tasks:
- Use the provided original HTML code as the starting point for redesign
- Preserve all original content, structure, and functionality
- Keep the same semantic HTML structure but enhance the styling
- Reuse all original images and their URLs from the HTML code
- Create a modern, responsive design with improved typography and spacing
- Use modern CSS frameworks and design patterns
- Ensure accessibility and mobile responsiveness
- Maintain the same navigation and user flow
- Enhance the visual design while keeping the original layout structure

If an image is provided, analyze it and use the visual information to better understand the user's requirements.

Always respond with code that can be executed or rendered directly.

Always output only the HTML code inside a ```html ... ``` code block, and do not include any explanations or extra text."""

GENERIC_SYSTEM_PROMPT = """You are an expert {language} developer. Write clean, idiomatic, and runnable {language} code for the user's request. If possible, include comments and best practices. Output ONLY the code inside a ```{language} ... ``` code block, and do not include any explanations or extra text. If the user provides a file or other context, use it as a reference. If the code is for a script or app, make it as self-contained as possible."""

# System prompt with search capability
HTML_SYSTEM_PROMPT_WITH_SEARCH = """ONLY USE HTML, CSS AND JAVASCRIPT. If you want to use ICON make sure to import the library first. Try to create the best UI possible by using only HTML, CSS and JAVASCRIPT. MAKE IT RESPONSIVE USING MODERN CSS. Use as much as you can modern CSS for the styling, if you can't do something with modern CSS, then use custom CSS. Also, try to elaborate as much as you can, to create something unique. ALWAYS GIVE THE RESPONSE INTO A SINGLE HTML FILE

You have access to real-time web search. When needed, use web search to find the latest information, best practices, or specific technologies.

For website redesign tasks:
- Use the provided original HTML code as the starting point for redesign
- Preserve all original content, structure, and functionality
- Keep the same semantic HTML structure but enhance the styling
- Reuse all original images and their URLs from the HTML code
- Use web search to find current design trends and best practices for the specific type of website
- Create a modern, responsive design with improved typography and spacing
- Use modern CSS frameworks and design patterns
- Ensure accessibility and mobile responsiveness
- Maintain the same navigation and user flow
- Enhance the visual design while keeping the original layout structure

If an image is provided, analyze it and use the visual information to better understand the user's requirements.

Always respond with code that can be executed or rendered directly.

Always output only the HTML code inside a ```html ... ``` code block, and do not include any explanations or extra text."""

GENERIC_SYSTEM_PROMPT_WITH_SEARCH = """You are an expert {language} developer. You have access to real-time web search. When needed, use web search to find the latest information, best practices, or specific technologies for {language}.

Write clean, idiomatic, and runnable {language} code for the user's request. If possible, include comments and best practices. Output ONLY the code inside a ```{language} ... ``` code block, and do not include any explanations or extra text. If the user provides a file or other context, use it as a reference. If the code is for a script or app, make it as self-contained as possible."""

# Follow-up system prompt for modifying existing HTML files
FollowUpSystemPrompt = f"""You are an expert web developer modifying an existing HTML file.
The user wants to apply changes based on their request.
You MUST output ONLY the changes required using the following SEARCH/REPLACE block format. Do NOT output the entire file.
Explain the changes briefly *before* the blocks if necessary, but the code changes THEMSELVES MUST be within the blocks.
Format Rules:
1. Start with {SEARCH_START}
2. Provide the exact lines from the current code that need to be replaced.
3. Use {DIVIDER} to separate the search block from the replacement.
4. Provide the new lines that should replace the original lines.
5. End with {REPLACE_END}
6. You can use multiple SEARCH/REPLACE blocks if changes are needed in different parts of the file.
7. To insert code, use an empty SEARCH block (only {SEARCH_START} and {DIVIDER} on their lines) if inserting at the very beginning, otherwise provide the line *before* the insertion point in the SEARCH block and include that line plus the new lines in the REPLACE block.
8. To delete code, provide the lines to delete in the SEARCH block and leave the REPLACE block empty (only {DIVIDER} and {REPLACE_END} on their lines).
9. IMPORTANT: The SEARCH block must *exactly* match the current code, including indentation and whitespace.
Example Modifying Code:
```
Some explanation...
{SEARCH_START}
    <h1>Old Title</h1>
{DIVIDER}
    <h1>New Title</h1>
{REPLACE_END}
{SEARCH_START}
  </body>
{DIVIDER}
    <script>console.log("Added script");</script>
  </body>
{REPLACE_END}
```
Example Deleting Code:
```
Removing the paragraph...
{SEARCH_START}
  <p>This paragraph will be deleted.</p>
{DIVIDER}
{REPLACE_END}
```"""

# Available models
AVAILABLE_MODELS = [
    {
        "name": "Moonshot Kimi-K2",
        "id": "moonshotai/Kimi-K2-Instruct",
        "description": "Moonshot AI Kimi-K2-Instruct model for code generation and general tasks"
    },
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
    },
    {
        "name": "GLM-4.1V-9B-Thinking",
        "id": "THUDM/GLM-4.1V-9B-Thinking",
        "description": "GLM-4.1V-9B-Thinking model for multimodal code generation with image support"
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
    },
    {
        "title": "Website Redesign",
        "description": "Enter a website URL to extract its content and redesign it with a modern, responsive layout"
    },
    {
        "title": "Modify HTML",
        "description": "After generating HTML, ask me to modify it with specific changes using search/replace format"
    },
    {
        "title": "Search/Replace Example",
        "description": "Generate HTML first, then ask: 'Change the title to My New Title' or 'Add a blue background to the body'"
    }
]

# HF Inference Client
HF_TOKEN = os.getenv('HF_TOKEN')
if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN environment variable is not set. Please set it to your Hugging Face API token.")

def get_inference_client(model_id, provider="auto"):
    """Return an InferenceClient with provider based on model_id and user selection."""
    return InferenceClient(
        provider=provider,
        api_key=HF_TOKEN,
        bill_to="huggingface"
    )

# Type definitions
History = List[Tuple[str, str]]
Messages = List[Dict[str, str]]

# Tavily Search Client
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')
tavily_client = None
if TAVILY_API_KEY:
    try:
        tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
    except Exception as e:
        print(f"Failed to initialize Tavily client: {e}")
        tavily_client = None

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
    return [], [], None, ""  # Empty lists for both tuple format and chatbot messages, None for file, empty string for website URL

def update_image_input_visibility(model):
    """Update image input visibility based on selected model"""
    is_ernie_vl = model.get("id") == "baidu/ERNIE-4.5-VL-424B-A47B-Base-PT"
    is_glm_vl = model.get("id") == "THUDM/GLM-4.1V-9B-Thinking"
    return gr.update(visible=is_ernie_vl or is_glm_vl)

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

def apply_search_replace_changes(original_html: str, changes_text: str) -> str:
    """Apply search/replace changes to HTML content"""
    if not changes_text.strip():
        return original_html
    
    # Split the changes text into individual search/replace blocks
    blocks = []
    current_block = ""
    lines = changes_text.split('\n')
    
    for line in lines:
        if line.strip() == SEARCH_START:
            if current_block.strip():
                blocks.append(current_block.strip())
            current_block = line + '\n'
        elif line.strip() == REPLACE_END:
            current_block += line + '\n'
            blocks.append(current_block.strip())
            current_block = ""
        else:
            current_block += line + '\n'
    
    if current_block.strip():
        blocks.append(current_block.strip())
    
    modified_html = original_html
    
    for block in blocks:
        if not block.strip():
            continue
            
        # Parse the search/replace block
        lines = block.split('\n')
        search_lines = []
        replace_lines = []
        in_search = False
        in_replace = False
        
        for line in lines:
            if line.strip() == SEARCH_START:
                in_search = True
                in_replace = False
            elif line.strip() == DIVIDER:
                in_search = False
                in_replace = True
            elif line.strip() == REPLACE_END:
                in_replace = False
            elif in_search:
                search_lines.append(line)
            elif in_replace:
                replace_lines.append(line)
        
        # Apply the search/replace
        if search_lines:
            search_text = '\n'.join(search_lines).strip()
            replace_text = '\n'.join(replace_lines).strip()
            
            if search_text in modified_html:
                modified_html = modified_html.replace(search_text, replace_text)
            else:
                print(f"Warning: Search text not found in HTML: {search_text[:100]}...")
    
    return modified_html

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

def extract_website_content(url: str) -> str:
    """Extract HTML code and content from a website URL"""
    try:
        # Validate URL
        parsed_url = urlparse(url)
        if not parsed_url.scheme:
            url = "https://" + url
            parsed_url = urlparse(url)
        
        if not parsed_url.netloc:
            return "Error: Invalid URL provided"
        
        # Set comprehensive headers to mimic a real browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        
        # Create a session to maintain cookies and handle redirects
        session = requests.Session()
        session.headers.update(headers)
        
        # Make the request with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = session.get(url, timeout=15, allow_redirects=True)
                response.raise_for_status()
                break
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403 and attempt < max_retries - 1:
                    # Try with different User-Agent on 403
                    session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    continue
                else:
                    raise
        
        # Get the raw HTML content with proper encoding
        try:
            # Try to get the content with automatic encoding detection
            response.encoding = response.apparent_encoding
            raw_html = response.text
        except:
            # Fallback to UTF-8 if encoding detection fails
            raw_html = response.content.decode('utf-8', errors='ignore')
        
        # Debug: Check if we got valid HTML
        if not raw_html.strip().startswith('<!DOCTYPE') and not raw_html.strip().startswith('<html'):
            print(f"Warning: Response doesn't look like HTML. First 200 chars: {raw_html[:200]}")
            print(f"Response headers: {dict(response.headers)}")
            print(f"Response encoding: {response.encoding}")
            print(f"Apparent encoding: {response.apparent_encoding}")
            
            # Try alternative approaches
            try:
                raw_html = response.content.decode('latin-1', errors='ignore')
                print("Tried latin-1 decoding")
            except:
                try:
                    raw_html = response.content.decode('utf-8', errors='ignore')
                    print("Tried UTF-8 decoding")
                except:
                    raw_html = response.content.decode('cp1252', errors='ignore')
                    print("Tried cp1252 decoding")
        
        # Parse HTML content for analysis
        soup = BeautifulSoup(raw_html, 'html.parser')
        
        # Check if this is a JavaScript-heavy site
        script_tags = soup.find_all('script')
        if len(script_tags) > 10:
            print(f"Warning: This site has {len(script_tags)} script tags - it may be a JavaScript-heavy site")
            print("The content might be loaded dynamically and not available in the initial HTML")
        
        # Extract title
        title = soup.find('title')
        title_text = title.get_text().strip() if title else "No title found"
        
        # Extract meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc.get('content', '') if meta_desc else ""
        
        # Extract main content areas for analysis
        content_sections = []
        main_selectors = [
            'main', 'article', '.content', '.main-content', '.post-content',
            '#content', '#main', '.entry-content', '.post-body'
        ]
        
        for selector in main_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text().strip()
                if len(text) > 100:  # Only include substantial content
                    content_sections.append(text)
        
        # Extract navigation links for analysis
        nav_links = []
        nav_elements = soup.find_all(['nav', 'header'])
        for nav in nav_elements:
            links = nav.find_all('a')
            for link in links:
                link_text = link.get_text().strip()
                link_href = link.get('href', '')
                if link_text and link_href:
                    nav_links.append(f"{link_text}: {link_href}")
        
        # Extract and fix image URLs in the HTML
        img_elements = soup.find_all('img')
        for img in img_elements:
            src = img.get('src', '')
            if src:
                # Handle different URL formats
                if src.startswith('//'):
                    # Protocol-relative URL
                    absolute_src = 'https:' + src
                    img['src'] = absolute_src
                elif src.startswith('/'):
                    # Root-relative URL
                    absolute_src = urljoin(url, src)
                    img['src'] = absolute_src
                elif not src.startswith(('http://', 'https://')):
                    # Relative URL
                    absolute_src = urljoin(url, src)
                    img['src'] = absolute_src
                # If it's already absolute, keep it as is
                
                # Also check for data-src (lazy loading) and other common attributes
                data_src = img.get('data-src', '')
                if data_src and not src:
                    # Use data-src if src is empty
                    if data_src.startswith('//'):
                        absolute_data_src = 'https:' + data_src
                        img['src'] = absolute_data_src
                    elif data_src.startswith('/'):
                        absolute_data_src = urljoin(url, data_src)
                        img['src'] = absolute_data_src
                    elif not data_src.startswith(('http://', 'https://')):
                        absolute_data_src = urljoin(url, data_src)
                        img['src'] = absolute_data_src
                    else:
                        img['src'] = data_src
        
        # Also fix background image URLs in style attributes
        elements_with_style = soup.find_all(attrs={'style': True})
        for element in elements_with_style:
            style_attr = element.get('style', '')
            # Find and replace relative URLs in background-image
            import re
            bg_pattern = r'background-image:\s*url\(["\']?([^"\']+)["\']?\)'
            matches = re.findall(bg_pattern, style_attr, re.IGNORECASE)
            for match in matches:
                if match:
                    if match.startswith('//'):
                        absolute_bg = 'https:' + match
                        style_attr = style_attr.replace(match, absolute_bg)
                    elif match.startswith('/'):
                        absolute_bg = urljoin(url, match)
                        style_attr = style_attr.replace(match, absolute_bg)
                    elif not match.startswith(('http://', 'https://')):
                        absolute_bg = urljoin(url, match)
                        style_attr = style_attr.replace(match, absolute_bg)
            element['style'] = style_attr
        
        # Fix background images in <style> tags
        style_elements = soup.find_all('style')
        for style in style_elements:
            if style.string:
                style_content = style.string
                # Find and replace relative URLs in background-image
                bg_pattern = r'background-image:\s*url\(["\']?([^"\']+)["\']?\)'
                matches = re.findall(bg_pattern, style_content, re.IGNORECASE)
                for match in matches:
                    if match:
                        if match.startswith('//'):
                            absolute_bg = 'https:' + match
                            style_content = style_content.replace(match, absolute_bg)
                        elif match.startswith('/'):
                            absolute_bg = urljoin(url, match)
                            style_content = style_content.replace(match, absolute_bg)
                        elif not match.startswith(('http://', 'https://')):
                            absolute_bg = urljoin(url, match)
                            style_content = style_content.replace(match, absolute_bg)
                style.string = style_content
        
        # Extract images for analysis (after fixing URLs)
        images = []
        img_elements = soup.find_all('img')
        for img in img_elements:
            src = img.get('src', '')
            alt = img.get('alt', '')
            if src:
                images.append({'src': src, 'alt': alt})
        
        # Debug: Print some image URLs to see what we're getting
        print(f"Found {len(images)} images:")
        for i, img in enumerate(images[:5]):  # Show first 5 images
            print(f"  {i+1}. {img['alt'] or 'No alt'} - {img['src']}")
        
        # Test a few image URLs to see if they're accessible
        def test_image_url(img_url):
            try:
                test_response = requests.head(img_url, timeout=5, allow_redirects=True)
                return test_response.status_code == 200
            except:
                return False
        
        # Test first few images
        working_images = []
        for img in images[:10]:  # Test first 10 images
            if test_image_url(img['src']):
                working_images.append(img)
            else:
                print(f"  ❌ Broken image: {img['src']}")
        
        print(f"Working images: {len(working_images)} out of {len(images)}")
        
        # Get the modified HTML with absolute URLs
        modified_html = str(soup)
        
        # Clean and format the HTML for better readability
        # Remove unnecessary whitespace and comments
        import re
        cleaned_html = re.sub(r'<!--.*?-->', '', modified_html, flags=re.DOTALL)  # Remove HTML comments
        cleaned_html = re.sub(r'\s+', ' ', cleaned_html)  # Normalize whitespace
        cleaned_html = re.sub(r'>\s+<', '><', cleaned_html)  # Remove whitespace between tags
        
        # Limit HTML size to avoid token limits (keep first 15000 chars)
        if len(cleaned_html) > 15000:
            cleaned_html = cleaned_html[:15000] + "\n<!-- ... HTML truncated for length ... -->"
        
                # Check if we got any meaningful content
        if not title_text or title_text == "No title found":
            title_text = url.split('/')[-1] or url.split('/')[-2] or "Website"
        
        # If we couldn't extract any meaningful content, provide a fallback
        if len(cleaned_html.strip()) < 100:
            website_content = f"""
WEBSITE REDESIGN - EXTRACTION FAILED
====================================

URL: {url}
Title: {title_text}

ERROR: Could not extract meaningful HTML content from this website. This could be due to:
1. The website uses heavy JavaScript to load content dynamically
2. The website has anti-bot protection
3. The website requires authentication
4. The website is using advanced compression or encoding

FALLBACK APPROACH:
Please create a modern, responsive website design for a {title_text.lower()} website. Since I couldn't extract the original content, you can:

1. Create a typical layout for this type of website
2. Use placeholder content that would be appropriate
3. Include modern design elements and responsive features
4. Use a clean, professional design with good typography
5. Make it mobile-friendly and accessible

The website appears to be: {title_text}
"""
            return website_content.strip()
        
        # Compile the extracted content with the actual HTML code
        website_content = f"""
WEBSITE REDESIGN - ORIGINAL HTML CODE
=====================================

URL: {url}
Title: {title_text}
Description: {description}

PAGE ANALYSIS:
- This appears to be a {title_text.lower()} website
- Contains {len(content_sections)} main content sections
- Has {len(nav_links)} navigation links
- Includes {len(images)} images

IMAGES FOUND (use these exact URLs in your redesign):
{chr(10).join([f"• {img['alt'] or 'Image'} - {img['src']}" for img in working_images[:20]]) if working_images else "No working images found"}

ALL IMAGES (including potentially broken ones):
{chr(10).join([f"• {img['alt'] or 'Image'} - {img['src']}" for img in images[:20]]) if images else "No images found"}

ORIGINAL HTML CODE (use this as the base for redesign):
```html
{cleaned_html}
```

REDESIGN INSTRUCTIONS:
Please redesign this website with a modern, responsive layout while:
1. Preserving all the original content and structure
2. Maintaining the same navigation and functionality
3. Using the original images and their URLs (listed above)
4. Creating a modern, clean design with improved typography and spacing
5. Making it fully responsive for mobile devices
6. Using modern CSS frameworks and best practices
7. Keeping the same semantic structure but with enhanced styling

IMPORTANT: All image URLs in the HTML code above have been converted to absolute URLs and are ready to use. Make sure to preserve these exact image URLs in your redesigned version.

The HTML code above contains the complete original website structure with all images properly linked. Use it as your starting point and create a modernized version.
"""
        
        return website_content.strip()
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            return f"Error: Website blocked access (403 Forbidden). This website may have anti-bot protection. Try a different website or provide a description of what you want to build instead."
        elif e.response.status_code == 404:
            return f"Error: Website not found (404). Please check the URL and try again."
        elif e.response.status_code >= 500:
            return f"Error: Website server error ({e.response.status_code}). Please try again later."
        else:
            return f"Error accessing website: HTTP {e.response.status_code} - {str(e)}"
    except requests.exceptions.Timeout:
        return "Error: Request timed out. The website may be slow or unavailable."
    except requests.exceptions.ConnectionError:
        return "Error: Could not connect to the website. Please check your internet connection and the URL."
    except requests.exceptions.RequestException as e:
        return f"Error accessing website: {str(e)}"
    except Exception as e:
        return f"Error extracting website content: {str(e)}"

def generation_code(query: Optional[str], image: Optional[gr.Image], file: Optional[str], website_url: Optional[str], _setting: Dict[str, str], _history: Optional[History], _current_model: Dict, enable_search: bool = False, language: str = "html", provider: str = "auto"):
    if query is None:
        query = ''
    if _history is None:
        _history = []
    # Ensure _history is always a list of lists with at least 2 elements per item
    if not isinstance(_history, list):
        _history = []
    _history = [h for h in _history if isinstance(h, list) and len(h) == 2]

    # Check if there's existing HTML content in history to determine if this is a modification request
    has_existing_html = False
    last_assistant_msg = ""
    if _history and len(_history[-1]) > 1:
        last_assistant_msg = _history[-1][1]
        if '<!DOCTYPE html>' in last_assistant_msg or '<html' in last_assistant_msg:
            has_existing_html = True

    # Choose system prompt based on context
    if has_existing_html:
        # Use follow-up prompt for modifying existing HTML
        system_prompt = FollowUpSystemPrompt
    else:
        # Use language-specific prompt
        if language == "html":
            system_prompt = HTML_SYSTEM_PROMPT_WITH_SEARCH if enable_search else HTML_SYSTEM_PROMPT
        else:
            system_prompt = GENERIC_SYSTEM_PROMPT_WITH_SEARCH.format(language=language) if enable_search else GENERIC_SYSTEM_PROMPT.format(language=language)

    messages = history_to_messages(_history, system_prompt)

    # Extract file text and append to query if file is present
    file_text = ""
    if file:
        file_text = extract_text_from_file(file)
        if file_text:
            file_text = file_text[:5000]  # Limit to 5000 chars for prompt size
            query = f"{query}\n\n[Reference file content below]\n{file_text}"

    # Extract website content and append to query if website URL is present
    website_text = ""
    if website_url and website_url.strip():
        website_text = extract_website_content(website_url.strip())
        if website_text and not website_text.startswith("Error"):
            website_text = website_text[:8000]  # Limit to 8000 chars for prompt size
            query = f"{query}\n\n[Website content to redesign below]\n{website_text}"
        elif website_text.startswith("Error"):
            # Provide helpful guidance when website extraction fails
            fallback_guidance = """
Since I couldn't extract the website content, please provide additional details about what you'd like to build:

1. What type of website is this? (e.g., e-commerce, blog, portfolio, dashboard)
2. What are the main features you want?
3. What's the target audience?
4. Any specific design preferences? (colors, style, layout)

This will help me create a better design for you."""
            query = f"{query}\n\n[Error extracting website: {website_text}]{fallback_guidance}"

    # Enhance query with search if enabled
    enhanced_query = enhance_query_with_search(query, enable_search)

    # Use dynamic client based on selected model
    client = get_inference_client(_current_model["id"], provider)

    if image is not None:
        messages.append(create_multimodal_message(enhanced_query, image))
    else:
        messages.append({'role': 'user', 'content': enhanced_query})
    try:
        completion = client.chat.completions.create(
            model=_current_model["id"],
            messages=messages,
            stream=True,
            max_tokens=10000
        )
        content = ""
        for chunk in completion:
            # Only process if chunk.choices is non-empty
            if hasattr(chunk, "choices") and chunk.choices and hasattr(chunk.choices[0], "delta") and hasattr(chunk.choices[0].delta, "content"):
                content += chunk.choices[0].delta.content
                clean_code = remove_code_block(content)
                search_status = " (with web search)" if enable_search and tavily_client else ""
                if has_existing_html:
                    # Fallback: If the model returns a full HTML file, use it directly
                    if clean_code.strip().startswith("<!DOCTYPE html>") or clean_code.strip().startswith("<html"):
                        yield {
                            code_output: gr.update(value=clean_code, language=get_gradio_language(language)),
                            history_output: history_to_chatbot_messages(_history),
                            sandbox: send_to_sandbox(clean_code) if language == "html" else "<div style='padding:1em;color:#888;text-align:center;'>Preview is only available for HTML. Please download your code using the download button above.</div>",
                        }
                    else:
                        last_html = _history[-1][1] if _history and len(_history[-1]) > 1 else ""
                        modified_html = apply_search_replace_changes(last_html, clean_code)
                        clean_html = remove_code_block(modified_html)
                        yield {
                            code_output: gr.update(value=clean_html, language=get_gradio_language(language)),
                            history_output: history_to_chatbot_messages(_history),
                            sandbox: send_to_sandbox(clean_html) if language == "html" else "<div style='padding:1em;color:#888;text-align:center;'>Preview is only available for HTML. Please download your code using the download button above.</div>",
                        }
                else:
                    yield {
                        code_output: gr.update(value=clean_code, language=get_gradio_language(language)),
                        history_output: history_to_chatbot_messages(_history),
                        sandbox: send_to_sandbox(clean_code) if language == "html" else "<div style='padding:1em;color:#888;text-align:center;'>Preview is only available for HTML. Please download your code using the download button above.</div>",
                    }
            # Skip chunks with empty choices (end of stream)
            # Do not treat as error
        # Handle response based on whether this is a modification or new generation
        if has_existing_html:
            # Fallback: If the model returns a full HTML file, use it directly
            final_code = remove_code_block(content)
            if final_code.strip().startswith("<!DOCTYPE html>") or final_code.strip().startswith("<html"):
                clean_html = final_code
            else:
                last_html = _history[-1][1] if _history and len(_history[-1]) > 1 else ""
                modified_html = apply_search_replace_changes(last_html, final_code)
                clean_html = remove_code_block(modified_html)
            # Update history with the cleaned HTML
            _history.append([query, clean_html])
            yield {
                code_output: clean_html,
                history: _history,
                sandbox: send_to_sandbox(clean_html),
                history_output: history_to_chatbot_messages(_history),
            }
        else:
            # Regular generation - use the content as is
            _history.append([query, content])
            yield {
                code_output: remove_code_block(content),
                history: _history,
                sandbox: send_to_sandbox(remove_code_block(content)),
                history_output: history_to_chatbot_messages(_history),
            }
    except Exception as e:
        error_message = f"Error: {str(e)}"
        yield {
            code_output: error_message,
            history_output: history_to_chatbot_messages(_history),
        }

# Deploy to Spaces logic

def wrap_html_in_gradio_app(html_code):
    # Escape triple quotes for safe embedding
    safe_html = html_code.replace('"""', r'\"\"\"')
    return (
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

def deploy_to_spaces_static(code):
    if not code or not code.strip():
        return  # Do nothing if code is empty
    # Use the HTML code directly for static Spaces
    app_html = wrap_html_in_static_app(code.strip())
    base_url = "https://huggingface.co/new-space"
    params = urllib.parse.urlencode({
        "name": "new-space",
        "sdk": "static"
    })
    files_params = urllib.parse.urlencode({
        "files[0][path]": "index.html",
        "files[0][content]": app_html
    })
    full_url = f"{base_url}?{params}&{files_params}"
    webbrowser.open_new_tab(full_url)

# Main application
with gr.Blocks(
    theme=gr.themes.Base(
        primary_hue="blue",
        secondary_hue="gray",
        neutral_hue="gray",
        font=gr.themes.GoogleFont("Inter"),
        font_mono=gr.themes.GoogleFont("JetBrains Mono"),
        text_size=gr.themes.sizes.text_md,
        spacing_size=gr.themes.sizes.spacing_md,
        radius_size=gr.themes.sizes.radius_md
    ),
    title="AnyCoder - AI Code Generator"
) as demo:
    history = gr.State([])
    setting = gr.State({
        "system": HTML_SYSTEM_PROMPT,
    })
    current_model = gr.State(AVAILABLE_MODELS[0])  # Moonshot Kimi-K2
    open_panel = gr.State(None)
    last_login_state = gr.State(None)
    loaded_space_id = gr.State(None)

    with gr.Sidebar():
        login_button = gr.LoginButton()
        space_name_input = gr.Textbox(
            label="app name (e.g. my-cool-app)",
            placeholder="Enter your app name",
            lines=1,
            visible=True
        )
        deploy_btn = gr.Button("🚀 Deploy App", variant="primary")
        deploy_status = gr.Markdown(visible=False, label="Deploy status")
        
        # --- Load Space UI ---
        load_space_id = gr.Textbox(
            label="Load Space (username/space_name)",
            placeholder="e.g. huggingface-projects/hello-static",
            lines=1,
            visible=True
        )
        load_space_btn = gr.Button("Load Space", variant="secondary")
        load_space_status = gr.Markdown(visible=False)
        # --- End Load Space UI ---
        
        input = gr.Textbox(
            label="What would you like to build?",
            placeholder="Describe your application...",
            lines=3,
            visible=True  # Always visible
        )
        # Language dropdown for code generation
        language_choices = [
            "html", "python", "c", "cpp", "markdown", "latex", "json", "css", "javascript", "jinja2", "typescript", "yaml", "dockerfile", "shell", "r", "sql", "sql-msSQL", "sql-mySQL", "sql-mariaDB", "sql-sqlite", "sql-cassandra", "sql-plSQL", "sql-hive", "sql-pgSQL", "sql-gql", "sql-gpSQL", "sql-sparkSQL", "sql-esper"
        ]
        language_dropdown = gr.Dropdown(
            choices=language_choices,
            value="html",
            label="Code Language",
            visible=True  # Always visible
        )
        website_url_input = gr.Textbox(
            label="website for redesign",
            placeholder="https://example.com",
            lines=1,
            visible=True  # Always visible
        )
        file_input = gr.File(
            label="Reference file",
            file_types=[".pdf", ".txt", ".md", ".csv", ".docx", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".gif", ".webp"],
            visible=True  # Always visible
        )
        image_input = gr.Image(
            label="UI design image",
            visible=False  # Hidden by default; shown only for ERNIE-VL or GLM-VL
        )
        with gr.Row():
            btn = gr.Button("Generate", variant="primary", size="lg", scale=2, visible=True)  # Always visible
            clear_btn = gr.Button("Clear", variant="secondary", size="sm", scale=1, visible=True)  # Always visible
        search_toggle = gr.Checkbox(
            label="🔍 Web search",
            value=False,
            visible=True  # Always visible
        )
        model_dropdown = gr.Dropdown(
            choices=[model['name'] for model in AVAILABLE_MODELS],
            value=AVAILABLE_MODELS[0]['name'],  # Moonshot Kimi-K2
            label="Model",
            visible=True  # Always visible
        )
        provider_state = gr.State("auto")
        gr.Markdown("**Quick start**", visible=True)
        with gr.Column(visible=True) as quick_examples_col:
            for i, demo_item in enumerate(DEMO_LIST[:3]):
                demo_card = gr.Button(
                    value=demo_item['title'], 
                    variant="secondary",
                    size="sm"
                )
                demo_card.click(
                    fn=lambda idx=i: gr.update(value=DEMO_LIST[idx]['description']),
                    outputs=input
                )
        if not tavily_client:
            gr.Markdown("⚠️ Web search unavailable", visible=True)
        # Remove model display and web search available line
        def on_model_change(model_name):
            for m in AVAILABLE_MODELS:
                if m['name'] == model_name:
                    return m, update_image_input_visibility(m)
            return AVAILABLE_MODELS[0], update_image_input_visibility(AVAILABLE_MODELS[0])  # Moonshot Kimi-K2 fallback
        def save_prompt(input):
            return {setting: {"system": input}}
        model_dropdown.change(
            lambda model_name: on_model_change(model_name),
            inputs=model_dropdown,
            outputs=[current_model, image_input]
        )
        # Remove the Advanced accordion and system prompt editing UI
        # login_button.render()
        # space_name_input.render()

    with gr.Column():
        with gr.Tabs():
            with gr.Tab("Code"):
                code_output = gr.Code(
                    language="html", 
                    lines=25, 
                    interactive=False,
                    label="Generated code"
                )
            with gr.Tab("Preview"):
                sandbox = gr.HTML(label="Live preview")
            with gr.Tab("History"):
                history_output = gr.Chatbot(show_label=False, height=400, type="messages")

    # Event handlers
    def update_code_language(language):
        return gr.update(language=get_gradio_language(language))

    language_dropdown.change(update_code_language, inputs=language_dropdown, outputs=code_output)

    def preview_logic(code, language):
        if language == "html":
            return send_to_sandbox(code)
        else:
            return "<div style='padding:1em;color:#888;text-align:center;'>Preview is only available for HTML. Please download your code using the download button above.</div>"

    btn.click(
        generation_code,
        inputs=[input, image_input, file_input, website_url_input, setting, history, current_model, search_toggle, language_dropdown, provider_state],
        outputs=[code_output, history, sandbox, history_output]
    )
    # Update preview when code or language changes
    code_output.change(preview_logic, inputs=[code_output, language_dropdown], outputs=sandbox)
    language_dropdown.change(preview_logic, inputs=[code_output, language_dropdown], outputs=sandbox)
    clear_btn.click(clear_history, outputs=[history, history_output, file_input, website_url_input])

    # Deploy to Spaces logic

    def deploy_to_user_space(
        code, 
        space_name, 
        profile,   # OAuth profile from LoginButton
        token,     # OAuth token from LoginButton
        loaded_space_id=None
    ):
        if not code or not code.strip():
            return gr.update(value="No code to deploy.", visible=True)
        if profile is None or token is None:
            return gr.update(value="Please log in with your Hugging Face account to deploy to your own Space.", visible=True)
        api = HfApi(token=token)
        if loaded_space_id:
            repo_id = loaded_space_id
        else:
            username = profile.username
            repo_id = f"{username}/{space_name.strip()}"
            # Create the Space if it doesn't exist
            try:
                api.create_repo(
                    repo_id=repo_id,
                    repo_type="space",
                    space_sdk="static",
                    exist_ok=True
                )
            except Exception as e:
                return gr.update(value=f"Error creating Space: {e}", visible=True)
        # Save code to a temporary file
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
            f.write(code)
            temp_path = f.name
        # Upload the file
        try:
            api.upload_file(
                path_or_fileobj=temp_path,
                path_in_repo="index.html",
                repo_id=repo_id,
                repo_type="space"
            )
            space_url = f"https://huggingface.co/spaces/{repo_id}"
            return gr.update(value=f"✅ Deployed! [Open your Space here]({space_url})", visible=True)
        except Exception as e:
            return gr.update(value=f"Error uploading file: {e}", visible=True)

    # Connect the deploy button to the new function
    deploy_btn.click(
        deploy_to_user_space,
        inputs=[code_output, space_name_input, login_button, login_button, loaded_space_id],
        outputs=deploy_status
    )
    # Keep the old deploy method as fallback (if not logged in, user can still use the old method)
    # Optionally, you can keep the old deploy_btn.click for the default method as a secondary button.

    # --- Load Space logic ---
    from huggingface_hub import HfApi, hf_hub_download
    def load_space_index_html(space_id, history):
        api = HfApi()
        try:
            files = api.list_repo_files(space_id, repo_type="space")
            if "index.html" not in files:
                return gr.update(value="No index.html found in this Space.", visible=True), gr.update(value="", language="html"), None, "", gr.update(visible=True), history, None
            # Download the file
            local_path = hf_hub_download(repo_id=space_id, filename="index.html", repo_type="space")
            with open(local_path, "r", encoding="utf-8") as f:
                html_code = f.read()
            # Set as last assistant message in history
            new_history = history.copy() if history else []
            # Use a synthetic user message for clarity
            new_history.append([f"Loaded index.html from {space_id}", html_code])
            return (
                gr.update(value=f"Loaded index.html from {space_id}", visible=True),
                gr.update(value=html_code, language="html"),
                send_to_sandbox(html_code),
                history_to_chatbot_messages(new_history),
                gr.update(visible=True),
                new_history,
                space_id
            )
        except Exception as e:
            return gr.update(value=f"Error: {e}", visible=True), gr.update(value="", language="html"), None, "", gr.update(visible=True), history, None
    load_space_btn.click(
        load_space_index_html,
        inputs=[load_space_id, history],
        outputs=[load_space_status, code_output, sandbox, history_output, load_space_status, history, loaded_space_id]
    )
    # --- End Load Space logic ---

if __name__ == "__main__":
    demo.queue(api_open=False, default_concurrency_limit=20).launch(ssr_mode=True, mcp_server=False, show_api=False)