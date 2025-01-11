import ai_gradio

from utils_ai_gradio import get_app

# Get the Gemini models but keep their full names for loading
GEMINI_MODELS_FULL = [k for k in ai_gradio.registry if k.startswith("gemini:")]

# Create display names without the prefix
GEMINI_MODELS_DISPLAY = [k.replace("gemini:", "") for k in GEMINI_MODELS_FULL]

# Create and launch the interface using get_app utility
demo = get_app(
    models=GEMINI_MODELS_FULL,  # Use the full names with prefix
    default_model=GEMINI_MODELS_FULL[-2],
    dropdown_label="Select Gemini Model",
    choices=GEMINI_MODELS_DISPLAY,  # Display names without prefix
    src=ai_gradio.registry,
    enable_voice=True,
    fill_height=True,
)

if __name__ == "__main__":
    demo.launch()
