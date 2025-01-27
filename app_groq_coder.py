import ai_gradio

from utils_ai_gradio import get_app

# Get the Groq models but keep their full names for loading
GROQ_MODELS_FULL = [k for k in ai_gradio.registry.keys() if k.startswith("groq:")]

# Create display names without the prefix
GROQ_MODELS_DISPLAY = [k.replace("groq:", "") for k in GROQ_MODELS_FULL]

# Create and launch the interface using get_app utility
demo = get_app(
    models=GROQ_MODELS_FULL,  # Use the full names with prefix
    default_model=GROQ_MODELS_FULL[-1],
    dropdown_label="Select Groq Model",
    choices=GROQ_MODELS_DISPLAY,  # Display names without prefix
    fill_height=True,
    coder=True,
)


if __name__ == "__main__":
    demo.launch()
