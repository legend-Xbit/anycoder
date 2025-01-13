import ai_gradio

from utils_ai_gradio import get_app

# Get the hyperbolic models but keep their full names for loading
LANGCHAIN_MODELS_FULL = [k for k in ai_gradio.registry.keys() if k.startswith("langchain:")]

# Create display names without the prefix
LANGCHAIN_MODELS_DISPLAY = [k.replace("langchain:", "") for k in LANGCHAIN_MODELS_FULL]


# Create and launch the interface using get_app utility
demo = get_app(
    models=LANGCHAIN_MODELS_FULL,  # Use the full names with prefix
    default_model=LANGCHAIN_MODELS_FULL[0],
    dropdown_label="Select Langchain Model",
    choices=LANGCHAIN_MODELS_DISPLAY,  # Display names without prefix
    fill_height=True,
)

if __name__ == "__main__":
    demo.launch()

