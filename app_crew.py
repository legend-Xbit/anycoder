import ai_gradio
import gradio as gr

demo = gr.load(
    name="crewai:gpt-4-turbo",
    crew_type="article",  # or 'support'
    src=ai_gradio.registry,
)
