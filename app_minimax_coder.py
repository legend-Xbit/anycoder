import ai_gradio

from utils_ai_gradio import get_app

# Get the hyperbolic models but keep their full names for loading
MINIMAX_MODELS_FULL = [k for k in ai_gradio.registry.keys() if k.startswith("minimax:")]

# Create display names without the prefix
MINIMAX_MODELS_DISPLAY = [k.replace("minimax:", "") for k in MINIMAX_MODELS_FULL]


# Create and launch the interface using get_app utility
demo = get_app(
    models=MINIMAX_MODELS_FULL,  # Use the full names with prefix
    default_model=MINIMAX_MODELS_FULL[0],
    dropdown_label="Select Minimax Model",
    choices=MINIMAX_MODELS_DISPLAY,  # Display names without prefix
    fill_height=True,
    coder=True
)

if __name__ == "__main__":
    demo.launch()
