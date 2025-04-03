import ai_gradio

from utils_ai_gradio import get_app

# Get the hyperbolic models but keep their full names for loading
HUGGINGFACE_MODELS_FULL = [k for k in ai_gradio.registry.keys() if k.startswith("huggingface:")]

# Create display names without the prefix
HUGGINGFACE_MODELS_DISPLAY = [k.replace("huggingface:", "") for k in HUGGINGFACE_MODELS_FULL]


# Create and launch the interface using get_app utility
demo = get_app(
    models=HUGGINGFACE_MODELS_FULL,  # Use the full names with prefix
    default_model=HUGGINGFACE_MODELS_FULL[0],
    dropdown_label="Select Huggingface Model",
    choices=HUGGINGFACE_MODELS_DISPLAY,  # Display names without prefix
    fill_height=True,
    coder=True,
    provider="fireworks-ai",
    bill_to="huggingface"
)
