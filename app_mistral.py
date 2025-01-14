import ai_gradio

from utils_ai_gradio import get_app

# Get the mistral models but keep their full names for loading
MISTRAL_MODELS_FULL = [k for k in ai_gradio.registry.keys() if k.startswith("mistral:")]

# Create display names without the prefix
MISTRAL_MODELS_DISPLAY = [k.replace("mistral:", "") for k in MISTRAL_MODELS_FULL]


# Create and launch the interface using get_app utility
demo = get_app(
    models=MISTRAL_MODELS_FULL,  # Use the full names with prefix
    default_model=MISTRAL_MODELS_FULL[5],
    dropdown_label="Select Mistral Model",
    choices=MISTRAL_MODELS_DISPLAY,  # Display names without prefix
    fill_height=True,
    coder=True
)

if __name__ == "__main__":
    demo.launch()
