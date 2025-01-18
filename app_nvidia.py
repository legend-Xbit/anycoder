import ai_gradio

from utils_ai_gradio import get_app

# Get the nvidia models but keep their full names for loading
NVIDIA_MODELS_FULL = [k for k in ai_gradio.registry.keys() if k.startswith("nvidia:")]

# Create display names without the prefix
NVIDIA_MODELS_DISPLAY = [k.replace("nvidia:", "") for k in NVIDIA_MODELS_FULL]


# Create and launch the interface using get_app utility
demo = get_app(
    models=NVIDIA_MODELS_FULL,  # Use the full names with prefix
    default_model=NVIDIA_MODELS_FULL[0],
    dropdown_label="Select Nvidia Model",
    choices=NVIDIA_MODELS_DISPLAY,  # Display names without prefix
    fill_height=True,
)

if __name__ == "__main__":
    demo.launch()
