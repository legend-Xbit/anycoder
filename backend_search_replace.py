"""
Search/Replace utilities for applying targeted code changes.
Search/Replace utilities for applying targeted code changes.
"""

# Search/Replace block markers
SEARCH_START = "\u003c\u003c\u003c\u003c\u003c\u003c\u003c SEARCH"
DIVIDER = "======="
REPLACE_END = "\u003e\u003e\u003e\u003e\u003e\u003e\u003e REPLACE"


def apply_search_replace_changes(original_content: str, changes_text: str) -> str:
    """Apply search/replace changes to content (HTML, Python, JS, CSS, etc.)
    
    Args:
        original_content: The original file content to modify
        changes_text: Text containing SEARCH/REPLACE blocks
        
    Returns:
        Modified content with all search/replace blocks applied
    """
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
                        print(f"[Search/Replace] Warning: Search text not found in content: {search_text[:100]}...")
                except Exception:
                    print(f"[Search/Replace] Warning: Search text not found in content: {search_text[:100]}...")
    
    return modified_content


def has_search_replace_blocks(text: str) -> bool:
    """Check if text contains SEARCH/REPLACE block markers.
    
    Args:
        text: Text to check
        
    Returns:
        True if text contains search/replace markers, False otherwise
    """
    return (SEARCH_START in text) and (DIVIDER in text) and (REPLACE_END in text)


def parse_file_specific_changes(changes_text: str) -> dict:
    """Parse changes that specify which files to modify.
    
    Looks for patterns like:
        === components/Header.jsx ===
        \u003c\u003c\u003c\u003c\u003c\u003c\u003c SEARCH
        ...
        
    Returns:
        Dict mapping filename -> search/replace changes for that file
    """
    import re
    
    file_changes = {}
    
    # Pattern to match file sections: === filename ===
    file_pattern = re.compile(r"^===\s+([^\n=]+?)\s+===\s*$", re.MULTILINE)
    
    # Find all file sections
    matches = list(file_pattern.finditer(changes_text))
    
    if not matches:
        # No file-specific sections, treat entire text as changes
        return {"__all__": changes_text}
    
    for i, match in enumerate(matches):
        filename = match.group(1).strip()
        start_pos = match.end()
        
        # Find the end of this file's section (start of next file or end of text)
        if i + 1 < len(matches):
            end_pos = matches[i + 1].start()
        else:
            end_pos = len(changes_text)
        
        file_content = changes_text[start_pos:end_pos].strip()
        
        if file_content:
            file_changes[filename] = file_content
    
    return file_changes
