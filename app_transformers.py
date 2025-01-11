import gradio as gr

demo = gr.load(name="akhaliq/phi-4", src="spaces")

# Disable API access for all functions
if hasattr(demo, "fns"):
    for fn in demo.fns.values():
        fn.api_name = False

if __name__ == "__main__":
    demo.launch()
