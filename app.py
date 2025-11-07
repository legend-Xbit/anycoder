"""
AnyCoder - AI Code Generator
Main application entry point - now with modular architecture!
"""

# Import initialization functions from modules
from anycoder_app.docs_manager import (
    initialize_gradio_docs,
    initialize_comfyui_docs,
    initialize_fastrtc_docs
)
from anycoder_app.ui import demo

if __name__ == "__main__":
    # Initialize documentation systems
    print("Initializing Gradio documentation...")
    initialize_gradio_docs()
    
    print("Initializing ComfyUI documentation...")
    initialize_comfyui_docs()
    
    print("Initializing FastRTC documentation...")
    initialize_fastrtc_docs()
    
    # Launch the application
    print("Launching AnyCoder application...")
    demo.queue(api_open=False, default_concurrency_limit=20).launch(
        show_api=False, 
        ssr_mode=True, 
        mcp_server=False
    )
