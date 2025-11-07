"""
Gradio theme configurations for AnyCoder.
Provides multiple theme options with different visual styles.
"""
import os
import gradio as gr

def get_saved_theme():
    """Get the saved theme preference from file"""
    try:
        if os.path.exists('.theme_preference'):
            with open('.theme_preference', 'r') as f:
                return f.read().strip()
    except:
        pass
    return "Developer"
def save_theme_preference(theme_name):
    """Save theme preference to file"""
    try:
        with open('.theme_preference', 'w') as f:
            f.write(theme_name)
    except:
        pass

THEME_CONFIGS = {
    "Default": {
        "theme": gr.themes.Default(),
        "description": "Gradio's standard theme with clean orange accents"
    },
    "Base": {
        "theme": gr.themes.Base(
            primary_hue="blue",
            secondary_hue="slate",
            neutral_hue="slate",
            text_size="sm",
            spacing_size="sm",
            radius_size="md"
        ),
        "description": "Minimal foundation theme with blue accents"
    },
    "Soft": {
        "theme": gr.themes.Soft(
            primary_hue="emerald",
            secondary_hue="emerald",
            neutral_hue="slate",
            text_size="sm",
            spacing_size="md",
            radius_size="lg"
        ),
        "description": "Gentle rounded theme with soft emerald colors"
    },
    "Monochrome": {
        "theme": gr.themes.Monochrome(
            primary_hue="slate",
            secondary_hue="slate",
            neutral_hue="slate",
            text_size="sm",
            spacing_size="sm",
            radius_size="sm"
        ),
        "description": "Elegant black and white design"
    },
    "Glass": {
        "theme": gr.themes.Glass(
            primary_hue="blue",
            secondary_hue="blue",
            neutral_hue="slate",
            text_size="sm",
            spacing_size="md",
            radius_size="lg"
        ),
        "description": "Modern glassmorphism with blur effects"
    },
    "Dark Ocean": {
        "theme": gr.themes.Base(
            primary_hue="blue",
            secondary_hue="slate", 
            neutral_hue="slate",
            text_size="sm",
            spacing_size="sm",
            radius_size="md"
        ).set(
            body_background_fill="#0f172a",
            body_background_fill_dark="#0f172a",
            background_fill_primary="#3b82f6",
            background_fill_secondary="#1e293b",
            border_color_primary="#334155",
            block_background_fill="#1e293b",
            block_border_color="#334155",
            body_text_color="#f1f5f9",
            body_text_color_dark="#f1f5f9",
            block_label_text_color="#f1f5f9",
            block_label_text_color_dark="#f1f5f9",
            block_title_text_color="#f1f5f9",
            block_title_text_color_dark="#f1f5f9",
            input_background_fill="#0f172a",
            input_background_fill_dark="#0f172a",
            input_border_color="#334155",
            input_border_color_dark="#334155",
            button_primary_background_fill="#3b82f6",
            button_primary_border_color="#3b82f6",
            button_secondary_background_fill="#334155",
            button_secondary_border_color="#475569"
        ),
        "description": "Deep blue dark theme perfect for coding"
    },
    "Cyberpunk": {
        "theme": gr.themes.Base(
            primary_hue="fuchsia",
            secondary_hue="cyan",
            neutral_hue="slate",
            text_size="sm",
            spacing_size="sm",
            radius_size="none",
            font="Orbitron"
        ).set(
            body_background_fill="#0a0a0f",
            body_background_fill_dark="#0a0a0f",
            background_fill_primary="#ff10f0",
            background_fill_secondary="#1a1a2e",
            border_color_primary="#00f5ff",
            block_background_fill="#1a1a2e",
            block_border_color="#00f5ff",
            body_text_color="#00f5ff",
            body_text_color_dark="#00f5ff",
            block_label_text_color="#ff10f0",
            block_label_text_color_dark="#ff10f0",
            block_title_text_color="#ff10f0",
            block_title_text_color_dark="#ff10f0",
            input_background_fill="#0a0a0f",
            input_background_fill_dark="#0a0a0f",
            input_border_color="#00f5ff",
            input_border_color_dark="#00f5ff",
            button_primary_background_fill="#ff10f0",
            button_primary_border_color="#ff10f0",
            button_secondary_background_fill="#1a1a2e",
            button_secondary_border_color="#00f5ff"
        ),
        "description": "Futuristic neon cyber aesthetics"
    },
    "Forest": {
        "theme": gr.themes.Soft(
            primary_hue="emerald",
            secondary_hue="green",
            neutral_hue="emerald",
            text_size="sm",
            spacing_size="md",
            radius_size="lg"
        ).set(
            body_background_fill="#f0fdf4",
            body_background_fill_dark="#064e3b",
            background_fill_primary="#059669",
            background_fill_secondary="#ecfdf5",
            border_color_primary="#bbf7d0",
            block_background_fill="#ffffff",
            block_border_color="#d1fae5",
            body_text_color="#064e3b",
            body_text_color_dark="#f0fdf4",
            block_label_text_color="#064e3b",
            block_label_text_color_dark="#f0fdf4",
            block_title_text_color="#059669",
            block_title_text_color_dark="#10b981"
        ),
        "description": "Nature-inspired green earth tones"
    },
    "High Contrast": {
        "theme": gr.themes.Base(
            primary_hue="yellow",
            secondary_hue="slate",
            neutral_hue="slate",
            text_size="lg",
            spacing_size="lg",
            radius_size="sm"
        ).set(
            body_background_fill="#ffffff",
            body_background_fill_dark="#ffffff",
            background_fill_primary="#000000",
            background_fill_secondary="#ffffff",
            border_color_primary="#000000",
            block_background_fill="#ffffff",
            block_border_color="#000000",
            body_text_color="#000000",
            body_text_color_dark="#000000",
            block_label_text_color="#000000",
            block_label_text_color_dark="#000000",
            block_title_text_color="#000000",
            block_title_text_color_dark="#000000",
            input_background_fill="#ffffff",
            input_background_fill_dark="#ffffff",
            input_border_color="#000000",
            input_border_color_dark="#000000",
            button_primary_background_fill="#ffff00",
            button_primary_border_color="#000000",
            button_secondary_background_fill="#ffffff",
            button_secondary_border_color="#000000"
        ),
        "description": "Accessibility-focused high visibility"
    },
    "Developer": {
        "theme": gr.themes.Base(
            primary_hue="blue",
            secondary_hue="slate",
            neutral_hue="slate",
            text_size="sm",
            spacing_size="sm",
            radius_size="sm",
            font="Consolas"
        ).set(
            # VS Code exact colors
            body_background_fill="#1e1e1e",           # VS Code editor background
            body_background_fill_dark="#1e1e1e",
            background_fill_primary="#007acc",        # VS Code blue accent
            background_fill_secondary="#252526",      # VS Code sidebar background
            border_color_primary="#3e3e42",          # VS Code border color
            block_background_fill="#252526",         # VS Code panel background
            block_border_color="#3e3e42",           # VS Code subtle borders
            body_text_color="#cccccc",               # VS Code default text
            body_text_color_dark="#cccccc",
            block_label_text_color="#cccccc",
            block_label_text_color_dark="#cccccc",
            block_title_text_color="#ffffff",        # VS Code active text
            block_title_text_color_dark="#ffffff",
            input_background_fill="#2d2d30",         # VS Code input background
            input_background_fill_dark="#2d2d30",
            input_border_color="#3e3e42",           # VS Code input border
            input_border_color_dark="#3e3e42",
            input_border_color_focus="#007acc",      # VS Code focus border
            input_border_color_focus_dark="#007acc",
            button_primary_background_fill="#007acc", # VS Code button blue
            button_primary_border_color="#007acc",
            button_primary_background_fill_hover="#0e639c", # VS Code button hover
            button_secondary_background_fill="#2d2d30",
            button_secondary_border_color="#3e3e42",
            button_secondary_text_color="#cccccc"
        ),
        "description": "Authentic VS Code dark theme with exact color matching"
    }
}

# Additional theme information for developers
THEME_FEATURES = {
    "Default": ["Orange accents", "Clean layout", "Standard Gradio look"],
    "Base": ["Blue accents", "Minimal styling", "Clean foundation"],
    "Soft": ["Rounded corners", "Emerald colors", "Comfortable viewing"],
    "Monochrome": ["Black & white", "High elegance", "Timeless design"],
    "Glass": ["Glassmorphism", "Blur effects", "Translucent elements"],
    "Dark Ocean": ["Deep blue palette", "Dark theme", "Easy on eyes"],
    "Cyberpunk": ["Neon cyan/magenta", "Futuristic fonts", "Cyber vibes"],
    "Forest": ["Nature inspired", "Green tones", "Organic rounded"],
    "High Contrast": ["Black/white/yellow", "High visibility", "Accessibility"],
    "Developer": ["Authentic VS Code colors", "Consolas/Monaco fonts", "Exact theme matching"]
}

# Load saved theme and apply it
current_theme_name = get_saved_theme()
current_theme = THEME_CONFIGS[current_theme_name]["theme"]

