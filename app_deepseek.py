import gradio as gr
import ai_gradio

demo = gr.load(
    name='deepseek:deepseek-chat',
    src=ai_gradio.registry,
)