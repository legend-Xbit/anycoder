import ai_gradio

from utils_ai_gradio import get_app

# Get the hyperbolic models but keep their full names for loading
SAMBANOVA_MODELS_FULL = [k for k in ai_gradio.registry.keys() if k.startswith("sambanova:")]

# Create display names without the prefix
SAMBANOVA_MODELS_DISPLAY = [k.replace("sambanova:", "") for k in SAMBANOVA_MODELS_FULL]


# Create and launch the interface using get_app utility
demo = get_app(
    models=SAMBANOVA_MODELS_FULL,  # Use the full names with prefix
    default_model=SAMBANOVA_MODELS_FULL[-1],
    dropdown_label="Select Sambanova Model",
    choices=SAMBANOVA_MODELS_DISPLAY,  # Display names without prefix
    fill_height=True,
    coder=True,
)
