import os

import gemini_gradio

from utils import get_app

demo = get_app(
    models=[
        "gemini-2.0-flash-exp",
    ],
    default_model="gemini-2.0-flash-exp",
    src=gemini_gradio.registry,
    accept_token=not os.getenv("GEMINI_API_KEY"),
    enable_voice=True,
)

if __name__ == "__main__":
    demo.launch()
