import ai_gradio

from utils_ai_gradio import get_app

# Get the hyperbolic models but keep their full names for loading
DEEPSEEK_MODELS_FULL = [k for k in ai_gradio.registry.keys() if k.startswith("deepseek:")]

# Create display names without the prefix
DEEPSEEK_MODELS_DISPLAY = [k.replace("deepseek:", "") for k in DEEPSEEK_MODELS_FULL]


# Create and launch the interface using get_app utility
demo = get_app(
    models=DEEPSEEK_MODELS_FULL,  # Use the full names with prefix
    default_model=DEEPSEEK_MODELS_FULL[-1],
    dropdown_label="Select DeepSeek Model",
    choices=DEEPSEEK_MODELS_DISPLAY,  # Display names without prefix
    fill_height=True,
    coder=True,
)

if __name__ == "__main__":
    demo.launch()
