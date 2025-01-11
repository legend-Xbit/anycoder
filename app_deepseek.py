import ai_gradio
import gradio as gr

demo = gr.load(
    name="deepseek:deepseek-chat",
    src=ai_gradio.registry,
)
