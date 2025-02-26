from app_huggingface import demo as demo_huggingface
from app_openrouter import demo as demo_openrouter
from utils import get_app
import gradio as gr

# Create mapping of providers to their code snippets
PROVIDER_SNIPPETS = {
"Hugging Face": """           
import gradio as gr
import ai_gradio
gr.load(
    name='huggingface:meta-llama/Meta-Llama-3-8B-Instruct',
    src=ai_gradio.registry,
).launch()""",
"OpenRouter Coder": """
import gradio as gr
import ai_gradio
gr.load(
    name='openrouter:anthropic/claude-3.7-sonnet',
    src=ai_gradio.registry,
    coder=True
).launch()""",

    # Add similar snippets for other providers
}

# Create mapping of providers to their demos
PROVIDERS = {
    "Hugging Face": demo_huggingface,
    "OpenRouter Coder": demo_openrouter
}

# Modified get_app implementation
demo = gr.Blocks()
with demo:
    gr.Markdown("# Anychat")

    provider_dropdown = gr.Dropdown(
        choices=list(PROVIDERS.keys()),
        value="Hugging Face",
        label="Select code snippet"
    )
    code_display = gr.Code(
        label="Provider Code Snippet",
        language="python",
        value=PROVIDER_SNIPPETS["Hugging Face"]
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
        default_model="Hugging Face",
        src=PROVIDERS,
        dropdown_label="Select Provider",
    )

if __name__ == "__main__":
    demo.queue(api_open=False).launch(show_api=False)