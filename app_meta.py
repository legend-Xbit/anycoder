import gradio as gr

demo = gr.load("models/meta-llama/Llama-3.3-70B-Instruct")

if __name__ == "__main__":
    demo.launch()
