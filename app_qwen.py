import os

import ai_gradio

from utils import get_app

demo = get_app(
    models=[
        "qwen:qwen-turbo-latest",
        "qwen:qwen-turbo",
        "qwen:qwen-plus",
        "qwen:qwen-max",
        "qwen:qwen1.5-110b-chat",
        "qwen:qwen1.5-72b-chat",
        "qwen:qwen1.5-32b-chat",
        "qwen:qwen1.5-14b-chat",
        "qwen:qwen1.5-7b-chat",
        "qwen:qwq-32b-preview",
        "qwen:qvq-72b-preview",
    ],
    default_model="qwen:qvq-72b-preview",
    src=ai_gradio.registry,
    accept_token=not os.getenv("DASHSCOPE_API_KEY"),
)

if __name__ == "__main__":
    demo.launch()
