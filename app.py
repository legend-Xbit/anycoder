from app_huggingface import demo as demo_huggingface
from app_gemini_coder import demo as demo_gemini_coder
from utils import get_app
import gradio as gr

# Create mapping of providers to their code snippets
PROVIDER_SNIPPETS = {
"Hugging Face": """           
import gradio as gr
import ai_gradio
gr.load(
    name='huggingface:deepseek-ai/DeepSeek-R1',
    src=ai_gradio.registry,
    coder=True,
    provider="together"
).launch()""",
"Gemini Coder": """
    import gradio as gr
import ai_gradio
gr.load(
    name='gemini:gemini-1.5-pro',
    src=ai_gradio.registry,
    coder=True,
).launch()""",
}
# Create mapping of providers to their demos
PROVIDERS = {
    "Hugging Face": demo_huggingface,
    "Gemini Coder": demo_gemini_coder,
}

# Modified get_app implementation
demo = gr.Blocks()
with demo:
    gr.Markdown("# Anychat")

    provider_dropdown = gr.Dropdown(
        choices=list(PROVIDERS.keys()),
        value="Gemini Coder",
        label="Select code snippet"
    )
    code_display = gr.Code(
        label="Provider Code Snippet",
        language="python",
        value=PROVIDER_SNIPPETS["Gemini Coder"]
    )
    
    def update_code(provider):
        return PROVIDER_SNIPPETS.get(provider, "Code snippet not available")
    
   
    provider_dropdown.change(
        fn=update_code,
        inputs=[provider_dropdown],
        outputs=[code_display]
    )
    
    selected_demo = get_app(
        models=list(PROVIDERS.keys()),
        default_model="Gemini Coder",
        src=PROVIDERS,
        dropdown_label="Select Provider",
    )

if __name__ == "__main__":
    demo.queue(api_open=False).launch(show_api=False)