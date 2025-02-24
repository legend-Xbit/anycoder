import ai_gradio

from utils_ai_gradio import get_app

# Get the OpenAI models but keep their full names for loading
OPENROUTER_MODELS_FULL = [k for k in ai_gradio.registry.keys() if k.startswith("openrouter:")]

# Create display names without the prefix
OPENROUTER_MODELS_DISPLAY = [k.replace("openrouter:", "") for k in OPENROUTER_MODELS_FULL]

# Create and launch the interface using get_app utility
demo = get_app(
    models=OPENROUTER_MODELS_FULL,  # Use the full names with prefix
    default_model=OPENROUTER_MODELS_FULL[-1],
    dropdown_label="Select OpenRouter Model",
    choices=OPENROUTER_MODELS_DISPLAY,  # Display names without prefix
    fill_height=True,
    coder=True,
)

if __name__ == "__main__":
    demo.launch()
