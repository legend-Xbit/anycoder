import gradio as gr
import ai_gradio

demo = gr.load(
    name='transformers:phi-4',
    src=ai_gradio.registry
)

if __name__ == "__main__":
    demo.launch()
