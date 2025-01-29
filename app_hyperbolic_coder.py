import ai_gradio

from utils_ai_gradio import get_app

# Get the hyperbolic models but keep their full names for loading
HYPERBOLIC_MODELS_FULL = [k for k in ai_gradio.registry.keys() if k.startswith("hyperbolic:")]

# Create display names without the prefix
HYPERBOLIC_MODELS_DISPLAY = [k.replace("hyperbolic:", "") for k in HYPERBOLIC_MODELS_FULL]


# Create and launch the interface using get_app utility
demo = get_app(
    models=HYPERBOLIC_MODELS_FULL,  # Use the full names with prefix
    default_model=HYPERBOLIC_MODELS_FULL[-2],
    dropdown_label="Select Hyperbolic Model",
    choices=HYPERBOLIC_MODELS_DISPLAY,  # Display names without prefix
    fill_height=True,
    coder=True,
)
