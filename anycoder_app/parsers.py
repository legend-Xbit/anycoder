"""
Code parsing and formatting utilities for different frameworks.
Handles parsing of transformers.js, React, multi-file HTML, Streamlit, and Gradio code.
"""
import re
import os
import json
import base64
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
import html

from .config import SEARCH_START, DIVIDER, REPLACE_END

# Type definitions
History = List[Dict[str, str]]

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
            # Remove a leading language marker line (e.g., 'python') if present
            if extracted.split('\n', 1)[0].strip().lower() in ['python', 'html', 'css', 'javascript', 'json', 'c', 'cpp', 'markdown', 'latex', 'jinja2', 'typescript', 'yaml', 'dockerfile', 'shell', 'r', 'sql', 'sql-mssql', 'sql-mysql', 'sql-mariadb', 'sql-sqlite', 'sql-cassandra', 'sql-plSQL', 'sql-hive', 'sql-pgsql', 'sql-gql', 'sql-gpsql', 'sql-sparksql', 'sql-esper']:
                return extracted.split('\n', 1)[1] if '\n' in extracted else ''
            # If HTML markup starts later in the block (e.g., Poe injected preface), trim to first HTML root
            html_root_idx = None
            for tag in ['<!DOCTYPE html', '<html']:
                idx = extracted.find(tag)
                if idx != -1:
                    html_root_idx = idx if html_root_idx is None else min(html_root_idx, idx)
            if html_root_idx is not None and html_root_idx > 0:
                return extracted[html_root_idx:].strip()
            return extracted
    # If no code block is found, check if the entire text is HTML
    stripped = text.strip()
    if stripped.startswith('<!DOCTYPE html>') or stripped.startswith('<html') or stripped.startswith('<'):
        # If HTML root appears later (e.g., Poe preface), trim to first HTML root
        for tag in ['<!DOCTYPE html', '<html']:
            idx = stripped.find(tag)
            if idx > 0:
                return stripped[idx:].strip()
        return stripped
    # Special handling for python: remove python marker
    if text.strip().startswith('```python'):
        return text.strip()[9:-3].strip()
    # Remove a leading language marker line if present (fallback)
    lines = text.strip().split('\n', 1)
    if lines[0].strip().lower() in ['python', 'html', 'css', 'javascript', 'json', 'c', 'cpp', 'markdown', 'latex', 'jinja2', 'typescript', 'yaml', 'dockerfile', 'shell', 'r', 'sql', 'sql-mssql', 'sql-mysql', 'sql-mariadb', 'sql-sqlite', 'sql-cassandra', 'sql-plSQL', 'sql-hive', 'sql-pgsql', 'sql-gql', 'sql-gpsql', 'sql-sparksql', 'sql-esper']:
        return lines[1] if len(lines) > 1 else ''
    return text.strip()

## React CDN compatibility fixer removed per user preference

def strip_placeholder_thinking(text: str) -> str:
    """Remove placeholder 'Thinking...' status lines from streamed text."""
    if not text:
        return text
    # Matches lines like: "Thinking..." or "Thinking... (12s elapsed)"
    return re.sub(r"(?mi)^[\t ]*Thinking\.\.\.(?:\s*\(\d+s elapsed\))?[\t ]*$\n?", "", text)

def is_placeholder_thinking_only(text: str) -> bool:
    """Return True if text contains only 'Thinking...' placeholder lines (with optional elapsed)."""
    if not text:
        return False
    stripped = text.strip()
    if not stripped:
        return False
    return re.fullmatch(r"(?s)(?:\s*Thinking\.\.\.(?:\s*\(\d+s elapsed\))?\s*)+", stripped) is not None

def extract_last_thinking_line(text: str) -> str:
    """Extract the last 'Thinking...' line to display as status."""
    matches = list(re.finditer(r"Thinking\.\.\.(?:\s*\(\d+s elapsed\))?", text))
    return matches[-1].group(0) if matches else "Thinking..."

def parse_transformers_js_output(text):
    """Parse transformers.js output and extract the three files (index.html, index.js, style.css)"""
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
        html_match = re.search(pattern, text, re.IGNORECASE)
        if html_match:
            files['index.html'] = html_match.group(1).strip()
            break
    
    # Extract JavaScript content
    for pattern in js_patterns:
        js_match = re.search(pattern, text, re.IGNORECASE)
        if js_match:
            files['index.js'] = js_match.group(1).strip()
            break
    
    # Extract CSS content
    for pattern in css_patterns:
        css_match = re.search(pattern, text, re.IGNORECASE)
        if css_match:
            files['style.css'] = css_match.group(1).strip()
            break
    
    # Fallback: support === index.html === format if any file is missing
    if not (files['index.html'] and files['index.js'] and files['style.css']):
        # Use regex to extract sections
        html_fallback = re.search(r'===\s*index\.html\s*===\s*\n([\s\S]+?)(?=\n===|$)', text, re.IGNORECASE)
        js_fallback = re.search(r'===\s*index\.js\s*===\s*\n([\s\S]+?)(?=\n===|$)', text, re.IGNORECASE)
        css_fallback = re.search(r'===\s*style\.css\s*===\s*\n([\s\S]+?)(?=\n===|$)', text, re.IGNORECASE)
        
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
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    # Clean up the content by removing any code block markers
                    content = match.group(1).strip()
                    content = re.sub(r'^```\w*\s*\n', '', content)
                    content = re.sub(r'\n```\s*$', '', content)
                    files[file_key] = content.strip()
    
    return files

def format_transformers_js_output(files):
    """Format the three files into a single display string"""
    output = []
    output.append("=== index.html ===")
    output.append(files['index.html'])
    output.append("\n=== index.js ===")
    output.append(files['index.js'])
    output.append("\n=== style.css ===")
    output.append(files['style.css'])
    return '\n'.join(output)

def build_transformers_inline_html(files: dict) -> str:
    """Merge transformers.js three-file output into a single self-contained HTML document.

    - Inlines style.css into a <style> tag
    - Inlines index.js into a <script type="module"> tag
    - Rewrites ESM imports for transformers.js to a stable CDN URL so it works in data: iframes
    """
    import re as _re

    html = files.get('index.html') or ''
    js = files.get('index.js') or ''
    css = files.get('style.css') or ''

    # Normalize JS imports to CDN (handle both @huggingface/transformers and legacy @xenova/transformers)
    cdn_url = "https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.7.3"

    def _normalize_imports(_code: str) -> str:
        if not _code:
            return _code or ""
        _code = _re.sub(r"from\s+['\"]@huggingface/transformers['\"]", f"from '{cdn_url}'", _code)
        _code = _re.sub(r"from\s+['\"]@xenova/transformers['\"]", f"from '{cdn_url}'", _code)
        _code = _re.sub(r"from\s+['\"]https://cdn.jsdelivr.net/npm/@huggingface/transformers@[^'\"]+['\"]", f"from '{cdn_url}'", _code)
        _code = _re.sub(r"from\s+['\"]https://cdn.jsdelivr.net/npm/@xenova/transformers@[^'\"]+['\"]", f"from '{cdn_url}'", _code)
        return _code

    # Extract inline module scripts from index.html, then merge into JS so we control imports
    inline_modules = []
    try:
        for _m in _re.finditer(r"<script\\b[^>]*type=[\"\']module[\"\'][^>]*>([\s\S]*?)</script>", html, flags=_re.IGNORECASE):
            inline_modules.append(_m.group(1))
        if inline_modules:
            html = _re.sub(r"<script\\b[^>]*type=[\"\']module[\"\'][^>]*>[\s\S]*?</script>\\s*", "", html, flags=_re.IGNORECASE)
        # Normalize any external module script URLs that load transformers to a single CDN version (keep the tag)
        html = _re.sub(r"https://cdn\.jsdelivr\.net/npm/@huggingface/transformers@[^'\"<>\s]+", cdn_url, html)
        html = _re.sub(r"https://cdn\.jsdelivr\.net/npm/@xenova/transformers@[^'\"<>\s]+", cdn_url, html)
    except Exception:
        # Best-effort; continue
        pass

    # Merge inline module code with provided index.js, then normalize imports
    combined_js_parts = []
    if inline_modules:
        combined_js_parts.append("\n\n".join(inline_modules))
    if js:
        combined_js_parts.append(js)
    js = "\n\n".join([p for p in combined_js_parts if (p and p.strip())])
    js = _normalize_imports(js)

    # Prepend a small prelude to reduce persistent caching during preview
    # Also ensure a global `transformers` namespace exists for apps relying on it
    # Note: importing env alongside user's own imports is fine in ESM
    if js.strip():
        prelude = (
            f"import {{ env }} from '{cdn_url}';\n"
            "try { env.useBrowserCache = false; } catch (e) {}\n"
            "try { if (env && env.backends && env.backends.onnx && env.backends.onnx.wasm) { env.backends.onnx.wasm.numThreads = 1; env.backends.onnx.wasm.proxy = false; } } catch (e) {}\n"
            f"(async () => {{ try {{ if (typeof globalThis.transformers === 'undefined') {{ const m = await import('{cdn_url}'); globalThis.transformers = m; }} }} catch (e) {{}} }})();\n"
        )
        js = prelude + js

    # If index.html missing or doesn't look like a full document, create a minimal shell
    doc = html.strip()
    if not doc or ('<html' not in doc.lower()):
        doc = (
            "<!DOCTYPE html>\n"
            "<html>\n<head>\n<meta charset=\"UTF-8\">\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n<title>Transformers.js App</title>\n</head>\n"
            "<body>\n<div id=\"app\"></div>\n</body>\n</html>"
        )

    # Remove local references to style.css and index.js to avoid duplicates when inlining
    doc = _re.sub(r"<link[^>]+href=\"[^\"]*style\.css\"[^>]*>\s*", "", doc, flags=_re.IGNORECASE)
    doc = _re.sub(r"<script[^>]+src=\"[^\"]*index\.js\"[^>]*>\s*</script>\s*", "", doc, flags=_re.IGNORECASE)

    # Inline CSS: insert before </head> or create a <head>
    style_tag = f"<style>\n{css}\n</style>" if css else ""
    if style_tag:
        if '</head>' in doc.lower():
            # Preserve original casing by finding closing head case-insensitively
            match = _re.search(r"</head>", doc, flags=_re.IGNORECASE)
            if match:
                idx = match.start()
                doc = doc[:idx] + style_tag + doc[idx:]
        else:
            # No head; insert at top of body
            match = _re.search(r"<body[^>]*>", doc, flags=_re.IGNORECASE)
            if match:
                idx = match.end()
                doc = doc[:idx] + "\n" + style_tag + doc[idx:]
            else:
                # Append at beginning
                doc = style_tag + doc

    # Inline JS: insert before </body>
    script_tag = f"<script type=\"module\">\n{js}\n</script>" if js else ""
    # Lightweight debug console overlay to surface runtime errors inside the iframe
    debug_overlay = (
        "<style>\n"
        "#anycoder-debug{position:fixed;left:0;right:0;bottom:0;max-height:45%;overflow:auto;"
        "background:rgba(0,0,0,.85);color:#9eff9e;padding:.5em;font:12px/1.4 monospace;z-index:2147483647;display:none}"
        "#anycoder-debug pre{margin:0;white-space:pre-wrap;word-break:break-word}"
        "</style>\n"
        "<div id=\"anycoder-debug\"></div>\n"
        "<script>\n"
        "(function(){\n"
        "  const el = document.getElementById('anycoder-debug');\n"
        "  function show(){ if(el && el.style.display!=='block'){ el.style.display='block'; } }\n"
        "  function log(msg){ try{ show(); const pre=document.createElement('pre'); pre.textContent=msg; el.appendChild(pre);}catch(e){} }\n"
        "  const origError = console.error.bind(console);\n"
        "  console.error = function(){ origError.apply(console, arguments); try{ log('console.error: ' + Array.from(arguments).map(a=>{try{return (typeof a==='string')?a:JSON.stringify(a);}catch(e){return String(a);}}).join(' ')); }catch(e){} };\n"
        "  window.addEventListener('error', e => { log('window.onerror: ' + (e && e.message ? e.message : 'Unknown error')); });\n"
        "  window.addEventListener('unhandledrejection', e => { try{ const r=e && e.reason; log('unhandledrejection: ' + (r && (r.message || JSON.stringify(r)))); }catch(err){ log('unhandledrejection'); } });\n"
        "})();\n"
        "</script>"
    )
    # Cleanup script to clear Cache Storage and IndexedDB on unload to free model weights
    cleanup_tag = (
        "<script>\n"
        "(function(){\n"
        "  function cleanup(){\n"
        "    try { if (window.caches && caches.keys) { caches.keys().then(keys => keys.forEach(k => caches.delete(k))); } } catch(e){}\n"
        "    try { if (window.indexedDB && indexedDB.databases) { indexedDB.databases().then(dbs => dbs.forEach(db => db && db.name && indexedDB.deleteDatabase(db.name))); } } catch(e){}\n"
        "  }\n"
        "  window.addEventListener('pagehide', cleanup, { once: true });\n"
        "  window.addEventListener('beforeunload', cleanup, { once: true });\n"
        "})();\n"
        "</script>"
    )
    if script_tag:
        match = _re.search(r"</body>", doc, flags=_re.IGNORECASE)
        if match:
            idx = match.start()
            doc = doc[:idx] + debug_overlay + script_tag + cleanup_tag + doc[idx:]
        else:
            # Append at end
            doc = doc + debug_overlay + script_tag + cleanup_tag

    return doc

def send_transformers_to_sandbox(files: dict) -> str:
    """Build a self-contained HTML document from transformers.js files and return an iframe preview."""
    merged_html = build_transformers_inline_html(files)
    return send_to_sandbox(merged_html)

def parse_multipage_html_output(text: str) -> Dict[str, str]:
    """Parse multi-page HTML output formatted as repeated "=== filename ===" sections.

    Returns a mapping of filename → file content. Supports nested paths like assets/css/styles.css.
    """
    if not text:
        return {}
    # First, strip any markdown fences
    cleaned = remove_code_block(text)
    files: Dict[str, str] = {}
    import re as _re
    pattern = _re.compile(r"^===\s*([^=\n]+?)\s*===\s*\n([\s\S]*?)(?=\n===\s*[^=\n]+?\s*===|\Z)", _re.MULTILINE)
    for m in pattern.finditer(cleaned):
        name = m.group(1).strip()
        content = m.group(2).strip()
        # Remove accidental trailing fences if present
        content = _re.sub(r"^```\w*\s*\n|\n```\s*$", "", content)
        files[name] = content
    return files

def format_multipage_output(files: Dict[str, str]) -> str:
    """Format a dict of files back into === filename === sections.

    Ensures `index.html` appears first if present; others follow sorted by path.
    """
    if not isinstance(files, dict) or not files:
        return ""
    ordered_paths = []
    if 'index.html' in files:
        ordered_paths.append('index.html')
    for path in sorted(files.keys()):
        if path == 'index.html':
            continue
        ordered_paths.append(path)
    parts: list[str] = []
    for path in ordered_paths:
        parts.append(f"=== {path} ===")
        # Avoid trailing extra newlines to keep blocks compact
        parts.append((files.get(path) or '').rstrip())
    return "\n".join(parts)

def validate_and_autofix_files(files: Dict[str, str]) -> Dict[str, str]:
    """Ensure minimal contract for multi-file sites; auto-fix missing pieces.

    Rules:
    - Ensure at least one HTML entrypoint (index.html). If none, synthesize a simple index.html linking discovered pages.
    - For each HTML file, ensure referenced local assets exist in files; if missing, add minimal stubs.
    - Normalize relative paths (strip leading '/').
    """
    if not isinstance(files, dict) or not files:
        return files or {}
    import re as _re

    normalized: Dict[str, str] = {}
    for k, v in files.items():
        safe_key = k.strip().lstrip('/')
        normalized[safe_key] = v

    html_files = [p for p in normalized.keys() if p.lower().endswith('.html')]
    has_index = 'index.html' in normalized

    # If no index.html but some HTML pages exist, create a simple hub index linking to them
    if not has_index and html_files:
        links = '\n'.join([f"<li><a href=\"{p}\">{p}</a></li>" for p in html_files])
        normalized['index.html'] = (
            "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\"/>\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>\n"
            "<title>Site Index</title>\n</head>\n<body>\n<h1>Site</h1>\n<ul>\n"
            + links + "\n</ul>\n</body>\n</html>"
        )

    # Collect references from HTML files
    asset_refs: set[str] = set()
    link_href = _re.compile(r"<link[^>]+href=\"([^\"]+)\"")
    script_src = _re.compile(r"<script[^>]+src=\"([^\"]+)\"")
    img_src = _re.compile(r"<img[^>]+src=\"([^\"]+)\"")
    a_href = _re.compile(r"<a[^>]+href=\"([^\"]+)\"")

    for path, content in list(normalized.items()):
        if not path.lower().endswith('.html'):
            continue
        for patt in (link_href, script_src, img_src, a_href):
            for m in patt.finditer(content or ""):
                ref = (m.group(1) or "").strip()
                if not ref or ref.startswith('http://') or ref.startswith('https://') or ref.startswith('data:') or '#' in ref:
                    continue
                asset_refs.add(ref.lstrip('/'))

    # Add minimal stubs for missing local references (CSS/JS/pages only, not images)
    for ref in list(asset_refs):
        if ref not in normalized:
            if ref.lower().endswith('.css'):
                normalized[ref] = "/* generated stub */\n"
            elif ref.lower().endswith('.js'):
                normalized[ref] = "// generated stub\n"
            elif ref.lower().endswith('.html'):
                normalized[ref] = (
                    "<!DOCTYPE html>\n<html lang=\"en\">\n<head><meta charset=\"utf-8\"/><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/><title>Page</title></head>\n"
                    "<body><main><h1>Placeholder page</h1><p>This page was auto-created to satisfy an internal link.</p></main></body>\n</html>"
                )
            # Note: We no longer create placeholder image files automatically
            # This prevents unwanted SVG stub files from being generated during image generation

    return normalized
def inline_multipage_into_single_preview(files: Dict[str, str]) -> str:
    """Inline local CSS/JS referenced by index.html for preview inside a data: iframe.

    - Uses index.html as the base document
    - Inlines <link href="..."> if the target exists in files
    - Inlines <script src="..."> if the target exists in files
    - Leaves other links (e.g., about.html) untouched; preview covers the home page
    """
    import re as _re
    html = files.get('index.html', '')
    if not html:
        return ""
    doc = html
    # Inline CSS links that point to known files
    def _inline_css(match):
        href = match.group(1)
        if href in files:
            return f"<style>\n{files[href]}\n</style>"
        return match.group(0)
    doc = _re.sub(r"<link[^>]+href=\"([^\"]+)\"[^>]*/?>", _inline_css, doc, flags=_re.IGNORECASE)

    # Inline JS scripts that point to known files
    def _inline_js(match):
        src = match.group(1)
        if src in files:
            return f"<script>\n{files[src]}\n</script>"
        return match.group(0)
    doc = _re.sub(r"<script[^>]+src=\"([^\"]+)\"[^>]*>\s*</script>", _inline_js, doc, flags=_re.IGNORECASE)

    # Inject a lightweight in-iframe client-side navigator to load other HTML files
    try:
        import json as _json
        import base64 as _b64
        import re as _re
        html_pages = {k: v for k, v in files.items() if k.lower().endswith('.html')}
        # Ensure index.html entry restores the current body's HTML
        _m_body = _re.search(r"<body[^>]*>([\s\S]*?)</body>", doc, flags=_re.IGNORECASE)
        _index_body = _m_body.group(1) if _m_body else doc
        html_pages['index.html'] = _index_body
        encoded = _b64.b64encode(_json.dumps(html_pages).encode('utf-8')).decode('ascii')
        nav_script = (
            "<script>\n"  # Simple client-side loader for internal links
            "(function(){\n"
            f"  const MP_FILES = JSON.parse(atob('{encoded}'));\n"
            "  function extractBody(html){\n"
            "    try {\n"
            "      const doc = new DOMParser().parseFromString(html, 'text/html');\n"
            "      const title = doc.querySelector('title'); if (title) document.title = title.textContent || document.title;\n"
            "      return doc.body ? doc.body.innerHTML : html;\n"
            "    } catch(e){ return html; }\n"
            "  }\n"
            "  function loadPage(path){\n"
            "    if (!MP_FILES[path]) return false;\n"
            "    const bodyHTML = extractBody(MP_FILES[path]);\n"
            "    document.body.innerHTML = bodyHTML;\n"
            "    attach();\n"
            "    try { history.replaceState({}, '', '#'+path); } catch(e){}\n"
            "    return true;\n"
            "  }\n"
            "  function clickHandler(e){\n"
            "    const a = e.target && e.target.closest ? e.target.closest('a') : null;\n"
            "    if (!a) return;\n"
            "    const href = a.getAttribute('href') || '';\n"
            "    if (!href || href.startsWith('#') || /^https?:/i.test(href) || href.startsWith('mailto:') || href.startsWith('tel:')) return;\n"
            "    const clean = href.split('#')[0].split('?')[0];\n"
            "    if (MP_FILES[clean]) { e.preventDefault(); loadPage(clean); }\n"
            "  }\n"
            "  function attach(){ document.removeEventListener('click', clickHandler, true); document.addEventListener('click', clickHandler, true); }\n"
            "  document.addEventListener('DOMContentLoaded', function(){ attach(); const initial = (location.hash||'').slice(1); if (initial && MP_FILES[initial]) loadPage(initial); }, { once:true });\n"
            "})();\n"
            "</script>"
        )
        m = _re.search(r"</body>", doc, flags=_re.IGNORECASE)
        if m:
            i = m.start()
            doc = doc[:i] + nav_script + doc[i:]
        else:
            doc = doc + nav_script
    except Exception:
        # Non-fatal in preview
        pass

    return doc

def extract_html_document(text: str) -> str:
    """Return substring starting from the first <!DOCTYPE html> or <html> if present, else original text.

    This ignores prose or planning notes before the actual HTML so previews don't break.
    """
    if not text:
        return text
    lower = text.lower()
    idx = lower.find("<!doctype html")
    if idx == -1:
        idx = lower.find("<html")
    return text[idx:] if idx != -1 else text


def parse_react_output(text):
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


def history_render(history: History):
    return gr.update(visible=True), history

def clear_history():
    return [], []  # Empty lists for both history and chatbot messages

def create_multimodal_message(text, image=None):
    """Create a chat message. For broad provider compatibility, always return content as a string.

    Some providers (e.g., Hugging Face router endpoints like Cerebras) expect `content` to be a string,
    not a list of typed parts. To avoid 422 validation errors, we inline a brief note when an image is provided.
    """
    if image is None:
        return {"role": "user", "content": text}
    # Keep providers happy: avoid structured multimodal payloads; add a short note instead
    # If needed, this can be enhanced per-model with proper multimodal schemas.
    return {"role": "user", "content": f"{text}\n\n[An image was provided as reference.]"}
def apply_search_replace_changes(original_content: str, changes_text: str) -> str:
    """Apply search/replace changes to content (HTML, Python, etc.)"""
    if not changes_text.strip():
        return original_content
    
    # If the model didn't use the block markers, try a CSS-rule fallback where
    # provided blocks like `.selector { ... }` replace matching CSS rules.
    if (SEARCH_START not in changes_text) and (DIVIDER not in changes_text) and (REPLACE_END not in changes_text):
        try:
            import re  # Local import to avoid global side effects
            updated_content = original_content
            replaced_any_rule = False
            # Find CSS-like rule blocks in the changes_text
            # This is a conservative matcher that looks for `selector { ... }`
            css_blocks = re.findall(r"([^{]+)\{([\s\S]*?)\}", changes_text, flags=re.MULTILINE)
            for selector_raw, body_raw in css_blocks:
                selector = selector_raw.strip()
                body = body_raw.strip()
                if not selector:
                    continue
                # Build a regex to find the existing rule for this selector
                # Capture opening `{` and closing `}` to preserve them; replace inner body.
                pattern = re.compile(rf"({re.escape(selector)}\s*\{{)([\s\S]*?)(\}})")
                def _replace_rule(match):
                    nonlocal replaced_any_rule
                    replaced_any_rule = True
                    prefix, existing_body, suffix = match.groups()
                    # Preserve indentation of the existing first body line if present
                    first_line_indent = ""
                    for line in existing_body.splitlines():
                        stripped = line.lstrip(" \t")
                        if stripped:
                            first_line_indent = line[: len(line) - len(stripped)]
                            break
                    # Re-indent provided body with the detected indent
                    if body:
                        new_body_lines = [first_line_indent + line if line.strip() else line for line in body.splitlines()]
                        new_body_text = "\n" + "\n".join(new_body_lines) + "\n"
                    else:
                        new_body_text = existing_body  # If empty body provided, keep existing
                    return f"{prefix}{new_body_text}{suffix}"
                updated_content, num_subs = pattern.subn(_replace_rule, updated_content, count=1)
            if replaced_any_rule:
                return updated_content
        except Exception:
            # Fallback silently to the standard block-based application
            pass

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
    
    modified_content = original_content
    
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
            
            if search_text in modified_content:
                modified_content = modified_content.replace(search_text, replace_text)
            else:
                # If exact block match fails, attempt a CSS-rule fallback using the replace_text
                try:
                    import re
                    updated_content = modified_content
                    replaced_any_rule = False
                    css_blocks = re.findall(r"([^{]+)\{([\s\S]*?)\}", replace_text, flags=re.MULTILINE)
                    for selector_raw, body_raw in css_blocks:
                        selector = selector_raw.strip()
                        body = body_raw.strip()
                        if not selector:
                            continue
                        pattern = re.compile(rf"({re.escape(selector)}\s*\{{)([\s\S]*?)(\}})")
                        def _replace_rule(match):
                            nonlocal replaced_any_rule
                            replaced_any_rule = True
                            prefix, existing_body, suffix = match.groups()
                            first_line_indent = ""
                            for line in existing_body.splitlines():
                                stripped = line.lstrip(" \t")
                                if stripped:
                                    first_line_indent = line[: len(line) - len(stripped)]
                                    break
                            if body:
                                new_body_lines = [first_line_indent + line if line.strip() else line for line in body.splitlines()]
                                new_body_text = "\n" + "\n".join(new_body_lines) + "\n"
                            else:
                                new_body_text = existing_body
                            return f"{prefix}{new_body_text}{suffix}"
                        updated_content, num_subs = pattern.subn(_replace_rule, updated_content, count=1)
                    if replaced_any_rule:
                        modified_content = updated_content
                    else:
                        print(f"Warning: Search text not found in content: {search_text[:100]}...")
                except Exception:
                    print(f"Warning: Search text not found in content: {search_text[:100]}...")
    
    return modified_content

def apply_transformers_js_search_replace_changes(original_formatted_content: str, changes_text: str) -> str:
    """Apply search/replace changes to transformers.js formatted content (three files)"""
    if not changes_text.strip():
        return original_formatted_content
    
    # Parse the original formatted content to get the three files
    files = parse_transformers_js_output(original_formatted_content)
    
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
    
    # Process each block and apply changes to the appropriate file
    for block in blocks:
        if not block.strip():
            continue
            
        # Parse the search/replace block
        lines = block.split('\n')
        search_lines = []
        replace_lines = []
        in_search = False
        in_replace = False
        target_file = None
        
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
        
        # Determine which file this change targets based on the search content
        if search_lines:
            search_text = '\n'.join(search_lines).strip()
            replace_text = '\n'.join(replace_lines).strip()
            
            # Check which file contains the search text
            if search_text in files['index.html']:
                target_file = 'index.html'
            elif search_text in files['index.js']:
                target_file = 'index.js'
            elif search_text in files['style.css']:
                target_file = 'style.css'
            
            # Apply the change to the target file
            if target_file and search_text in files[target_file]:
                files[target_file] = files[target_file].replace(search_text, replace_text)
            else:
                print(f"Warning: Search text not found in any transformers.js file: {search_text[:100]}...")
    
    # Reformat the modified files
    return format_transformers_js_output(files)

def send_to_sandbox(code):
    """Render HTML in a sandboxed iframe. Assumes full HTML is provided by prompts."""
    html_doc = (code or "").strip()
    # For preview only: inline local file URLs as data URIs so the
    # data: iframe can load them. The original code (shown to the user) still contains file URLs.
    try:
        import re
        import base64 as _b64
        import mimetypes as _mtypes
        import urllib.parse as _uparse
        def _file_url_to_data_uri(file_url: str) -> Optional[str]:
            try:
                parsed = _uparse.urlparse(file_url)
                path = _uparse.unquote(parsed.path)
                if not path:
                    return None
                with open(path, 'rb') as _f:
                    raw = _f.read()
                mime = _mtypes.guess_type(path)[0] or 'application/octet-stream'
                
                b64 = _b64.b64encode(raw).decode()
                return f"data:{mime};base64,{b64}"
            except Exception as e:
                print(f"[Sandbox] Failed to convert file URL to data URI: {str(e)}")
                return None
        def _repl_double(m):
            url = m.group(1)
            data_uri = _file_url_to_data_uri(url)
            return f'src="{data_uri}"' if data_uri else m.group(0)
        def _repl_single(m):
            url = m.group(1)
            data_uri = _file_url_to_data_uri(url)
            return f"src='{data_uri}'" if data_uri else m.group(0)
        html_doc = re.sub(r'src="(file:[^"]+)"', _repl_double, html_doc)
        html_doc = re.sub(r"src='(file:[^']+)'", _repl_single, html_doc)
                
    except Exception:
        # Best-effort; continue without inlining
        pass
    encoded_html = base64.b64encode(html_doc.encode('utf-8')).decode('utf-8')
    data_uri = f"data:text/html;charset=utf-8;base64,{encoded_html}"
    iframe = f'<iframe src="{data_uri}" width="100%" height="920px" sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals allow-presentation" allow="display-capture"></iframe>'
    return iframe

def is_streamlit_code(code: str) -> bool:
    """Heuristic check to determine if Python code is a Streamlit app."""
    if not code:
        return False
    lowered = code.lower()
    return ("import streamlit" in lowered) or ("from streamlit" in lowered) or ("st." in code and "streamlit" in lowered)

def clean_requirements_txt_content(content: str) -> str:
    """
    Clean up requirements.txt content to remove markdown formatting.
    This function removes code blocks, markdown lists, headers, and other formatting
    that might be mistakenly included by LLMs.
    """
    if not content:
        return content
    
    # First, remove code blocks if present
    if '```' in content:
        content = remove_code_block(content)
    
    # Process line by line to remove markdown formatting
    lines = content.split('\n')
    clean_lines = []
    
    for line in lines:
        stripped_line = line.strip()
        
        # Skip empty lines
        if not stripped_line:
            continue
        
        # Skip lines that are markdown formatting
        if (stripped_line == '```' or 
            stripped_line.startswith('```') or
            # Skip markdown headers (## Header) but keep comments (# comment)
            (stripped_line.startswith('#') and len(stripped_line) > 1 and stripped_line[1] != ' ') or
            stripped_line.startswith('**') or  # Skip bold text
            stripped_line.startswith('===') or  # Skip section dividers
            stripped_line.startswith('---') or  # Skip horizontal rules
            # Skip common explanatory text patterns
            stripped_line.lower().startswith('here') or
            stripped_line.lower().startswith('this') or
            stripped_line.lower().startswith('the ') or
            stripped_line.lower().startswith('based on') or
            stripped_line.lower().startswith('dependencies') or
            stripped_line.lower().startswith('requirements')):
            continue
        
        # Handle markdown list items (- item or * item)
        if (stripped_line.startswith('- ') or stripped_line.startswith('* ')):
            # Extract the package name after the list marker
            stripped_line = stripped_line[2:].strip()
            if not stripped_line:
                continue
        
        # Keep lines that look like valid package specifications
        # Valid lines: package names, git+https://, comments starting with "# "
        if (stripped_line.startswith('# ') or  # Valid comments
            stripped_line.startswith('git+') or  # Git dependencies
            stripped_line[0].isalnum() or  # Package names start with alphanumeric
            '==' in stripped_line or  # Version specifications
            '>=' in stripped_line or  # Version specifications
            '<=' in stripped_line or  # Version specifications
            '~=' in stripped_line):  # Version specifications
            clean_lines.append(stripped_line)
    
    result = '\n'.join(clean_lines)
    
    # Ensure it ends with a newline
    if result and not result.endswith('\n'):
        result += '\n'
    
    return result if result else "# No additional dependencies required\n"

def parse_multi_file_python_output(code: str) -> dict:
    """Parse multi-file Python output (Gradio/Streamlit) into separate files"""
    files = {}
    if not code:
        return files
    
    # Look for file separators like === filename.py ===
    import re
    file_pattern = r'=== ([^=]+) ==='
    parts = re.split(file_pattern, code)
    
    if len(parts) > 1:
        # Multi-file format detected
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                filename = parts[i].strip()
                content = parts[i + 1].strip()
                
                # Clean up requirements.txt to remove markdown formatting
                if filename == 'requirements.txt':
                    content = clean_requirements_txt_content(content)
                
                files[filename] = content
    else:
        # Single file - check if it's a space import or regular code
        if "IMPORTED PROJECT FROM HUGGING FACE SPACE" in code:
            # This is already a multi-file import, try to parse it
            lines = code.split('\n')
            current_file = None
            current_content = []
            
            for line in lines:
                if line.startswith('=== ') and line.endswith(' ==='):
                    # Save previous file
                    if current_file and current_content:
                        content = '\n'.join(current_content)
                        # Clean up requirements.txt to remove markdown formatting
                        if current_file == 'requirements.txt':
                            content = clean_requirements_txt_content(content)
                        files[current_file] = content
                    # Start new file
                    current_file = line[4:-4].strip()
                    current_content = []
                elif current_file:
                    current_content.append(line)
            
            # Save last file
            if current_file and current_content:
                content = '\n'.join(current_content)
                # Clean up requirements.txt to remove markdown formatting
                if current_file == 'requirements.txt':
                    content = clean_requirements_txt_content(content)
                files[current_file] = content
        else:
            # Single file code - determine appropriate filename
            if is_streamlit_code(code):
                files['streamlit_app.py'] = code
            elif 'import gradio' in code.lower() or 'from gradio' in code.lower():
                files['app.py'] = code
            else:
                files['app.py'] = code
    
    return files

def format_multi_file_python_output(files: dict) -> str:
    """Format multiple Python files into the standard multi-file format"""
    if not files:
        return ""
    
    if len(files) == 1:
        # Single file - return as is
        return list(files.values())[0]
    
    # Multi-file format
    output = []
    
    # Order files: main app first, then utils, models, config, requirements
    file_order = ['app.py', 'streamlit_app.py', 'main.py', 'utils.py', 'models.py', 'config.py', 'requirements.txt']
    ordered_files = []
    
    # Add files in preferred order
    for preferred_file in file_order:
        if preferred_file in files:
            ordered_files.append(preferred_file)
    
    # Add remaining files
    for filename in sorted(files.keys()):
        if filename not in ordered_files:
            ordered_files.append(filename)
    
    # Format output
    for filename in ordered_files:
        output.append(f"=== {filename} ===")
        
        # Clean up requirements.txt content if it's being formatted
        content = files[filename]
        if filename == 'requirements.txt':
            content = clean_requirements_txt_content(content)
        
        output.append(content)
        output.append("")  # Empty line between files
    
    return '\n'.join(output)

def send_streamlit_to_stlite(code: str) -> str:
    """Render Streamlit code using stlite inside a sandboxed iframe for preview."""
    # Build an HTML document that loads stlite and mounts the Streamlit app defined inline
    html_doc = (
        """<!doctype html>
<html>
  <head>
    <meta charset=\"UTF-8\" />
    <meta http-equiv=\"X-UA-Compatible\" content=\"IE=edge\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1, shrink-to-fit=no\" />
    <title>Streamlit Preview</title>
    <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/@stlite/browser@0.86.0/build/stlite.css\" />
    <style>html,body{margin:0;padding:0;height:100%;} streamlit-app{display:block;height:100%;}</style>
    <script type=\"module\" src=\"https://cdn.jsdelivr.net/npm/@stlite/browser@0.86.0/build/stlite.js\"></script>
  </head>
  <body>
    <streamlit-app>
"""
        + (code or "")
        + """
    </streamlit-app>
  </body>
</html>
"""
    )
    encoded_html = base64.b64encode(html_doc.encode('utf-8')).decode('utf-8')
    data_uri = f"data:text/html;charset=utf-8;base64,{encoded_html}"
    iframe = f'<iframe src="{data_uri}" width="100%" height="920px" sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals allow-presentation" allow="display-capture"></iframe>'
    return iframe

def is_gradio_code(code: str) -> bool:
    """Heuristic check to determine if Python code is a Gradio app."""
    if not code:
        return False
    lowered = code.lower()
    return (
        "import gradio" in lowered
        or "from gradio" in lowered
        or "gr.Interface(" in code
        or "gr.Blocks(" in code
    )

def send_gradio_to_lite(code: str) -> str:
    """Render Gradio code using gradio-lite inside a sandboxed iframe for preview."""
    html_doc = (
        """<!doctype html>
<html>
  <head>
    <meta charset=\"UTF-8\" />
    <meta http-equiv=\"X-UA-Compatible\" content=\"IE=edge\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1, shrink-to-fit=no\" />
    <title>Gradio Preview</title>
    <script type=\"module\" crossorigin src=\"https://cdn.jsdelivr.net/npm/@gradio/lite/dist/lite.js\"></script>
    <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/@gradio/lite/dist/lite.css\" />
    <style>html,body{margin:0;padding:0;height:100%;} gradio-lite{display:block;height:100%;}</style>
  </head>
  <body>
    <gradio-lite>
"""
        + (code or "")
        + """
    </gradio-lite>
  </body>
</html>
"""
    )
    encoded_html = base64.b64encode(html_doc.encode('utf-8')).decode('utf-8')
    data_uri = f"data:text/html;charset=utf-8;base64,{encoded_html}"
    iframe = f'<iframe src="{data_uri}" width="100%" height="920px" sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals allow-presentation" allow="display-capture"></iframe>'
    return iframe

stop_generation = False

