import ai_gradio

from utils_ai_gradio import get_app

# Get the Groq models from the registry
GROQ_MODELS_FULL = [k for k in ai_gradio.registry.keys() if k.startswith("groq:")]

# Create display names without the prefix
GROQ_MODELS_DISPLAY = [k.replace("groq:", "") for k in GROQ_MODELS_FULL]

demo = get_app(
    models=GROQ_MODELS_FULL,
    default_model=GROQ_MODELS_FULL[-2],
    src=ai_gradio.registry,
    dropdown_label="Select Groq Model",
    choices=GROQ_MODELS_DISPLAY,
    fill_height=True,
)

if __name__ == "__main__":
    demo.launch()
