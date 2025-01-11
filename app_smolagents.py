import ai_gradio

from utils_ai_gradio import get_app

SMOLAGENTS_MODELS_FULL = [k for k in ai_gradio.registry.keys() if k.startswith("smolagents:")]


SMOLAGENTS_MODELS_DISPLAY = [k.replace("smolagents:", "") for k in SMOLAGENTS_MODELS_FULL]

demo = get_app(
    models=SMOLAGENTS_MODELS_FULL,  # Use the full names with prefix
    default_model=SMOLAGENTS_MODELS_FULL[-1],
    dropdown_label="Select SmolAgents Model",
    choices=SMOLAGENTS_MODELS_DISPLAY,  # Display names without prefix
    fill_height=True,
)

if __name__ == "__main__":
    demo.launch()
