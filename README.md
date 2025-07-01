---
title: Anycoder
emoji: 🏢
colorFrom: indigo
colorTo: indigo
sdk: gradio
sdk_version: 5.23.3
app_file: app.py
pinned: false
disable_embedding: true
---

Check out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference

# Anycoder - AI Code Generation with Hugging Face Inference

An ultra-clean AI-powered code generation application using Hugging Face inference providers. Minimal files for maximum simplicity.

## Features

- **Hugging Face Models**: Uses DeepSeek-V3-0324 via Novita provider
- **Modern UI**: Built with Gradio and ModelScope Studio components
- **Code Generation**: Generates working code based on user requirements
- **Live Preview**: Renders generated HTML code in real-time
- **History Management**: Keeps track of conversation history
- **Streaming**: Real-time code generation with streaming responses

## Project Structure

```
anycoder/
├── app.py          # Main application (everything included)
├── app.css         # Basic styling
├── pyproject.toml  # Dependencies
└── README.md       # This file
```

## Setup

1. Set your Hugging Face API token:
   ```bash
   export HF_TOKEN="your_huggingface_token_here"
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Run the application:
   ```bash
   uv run python app.py
   ```

## Usage

1. Enter your application requirements in the text area
2. Click "send" to generate code
3. View the generated code in the code drawer
4. See the live preview in the sandbox area
5. Use example cards for quick prompts

## Code Example

```python
import os
from huggingface_hub import InferenceClient

client = InferenceClient(
    provider="novita",
    api_key=os.environ["HF_TOKEN"],
    bill_to="huggingface"
)

completion = client.chat.completions.create(
    model="deepseek-ai/DeepSeek-V3-0324",
    messages=[
        {
            "role": "user",
            "content": "Create a simple todo app"
        }
    ],
)
```

## Architecture

The application uses:
- **Gradio**: For the web interface
- **Hugging Face Hub**: For model inference
- **ModelScope Studio**: For UI components
- **Streaming**: For real-time code generation