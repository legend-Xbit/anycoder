import ai_gradio

from utils_ai_gradio import get_app

# Get the qwen models but keep their full names for loading
QWEN_MODELS_FULL = [k for k in ai_gradio.registry.keys() if k.startswith("qwen:")]

# Create display names without the prefix
QWEN_MODELS_DISPLAY = [k.replace("qwen:", "") for k in QWEN_MODELS_FULL]


# Create and launch the interface using get_app utility
demo = get_app(
    models=QWEN_MODELS_FULL,  # Use the full names with prefix
    default_model=QWEN_MODELS_FULL[-1],
    dropdown_label="Select Qwen Model",
    choices=QWEN_MODELS_DISPLAY,  # Display names without prefix
    fill_height=True,
    coder=True,
)
