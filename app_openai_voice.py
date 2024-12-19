import os

import openai_gradio

from utils import get_app

demo = get_app(
    models=[
        "gpt-4o-realtime-preview",
        "gpt-4o-realtime-preview-2024-12-17",
        "gpt-4o-realtime-preview-2024-10-01",
        "gpt-4o-mini-realtime-preview",
        "gpt-4o-mini-realtime-preview-2024-12-17",
    ],
    default_model="gpt-4o-mini-realtime-preview-2024-12-17",
    src=openai_gradio.registry,
    accept_token=not os.getenv("OPENAI_API_KEY"),
    twilio_sid=os.getenv("TWILIO_SID_OPENAI"),
    twilio_token=os.getenv("TWILIO_AUTH_OPENAI"),
)

if __name__ == "__main__":
    demo.launch()
