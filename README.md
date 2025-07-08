---
title: Anycoder
emoji: 🏢
colorFrom: indigo
colorTo: indigo
sdk: gradio
sdk_version: 5.35.0
app_file: app.py
pinned: false
disable_embedding: true
hf_oauth: true
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
- **OAuth Login Required**: Users must sign in with their Hugging Face account to use code generation features

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

1. **Sign in with your Hugging Face account** using the login button at the top left.
2. Enter your application requirements in the text area
3. Click "send" to generate code
4. View the generated code in the code drawer
5. See the live preview in the sandbox area
6. Use example cards for quick prompts

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
- **OAuth Login**: Requires users to sign in with Hugging Face for code generation
- **Streaming**: For real-time code generation

# Hugging Face Coder

A Gradio-based application that uses Hugging Face models to generate code based on user requirements. The app supports both text-only and multimodal (text + image) code generation.

## Features

- **Multiple Model Support**: DeepSeek V3, DeepSeek R1, and ERNIE-4.5-VL
- **Multimodal Input**: Upload images to help describe your requirements
- **Real-time Code Generation**: Stream responses from the models
- **Live Preview**: See your generated code in action with the built-in sandbox
- **History Management**: Keep track of your previous generations
- **Example Templates**: Quick-start with predefined application templates

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set your Hugging Face API token as an environment variable:
```bash
export HF_TOKEN="your_huggingface_token_here"
```

3. Run the application:
```bash
python app.py
```

## Usage

1. **Text-only Generation**: Simply type your requirements in the text area
2. **Multimodal Generation**: Upload an image and describe what you want to create
3. **Model Selection**: Switch between different models using the model selector
4. **Examples**: Use the provided example templates to get started quickly

## Supported Models

- **DeepSeek V3**: General code generation
- **DeepSeek R1**: Advanced code generation
- **ERNIE-4.5-VL**: Multimodal code generation with image understanding

## Environment Variables

- `HF_TOKEN`: Your Hugging Face API token (required)

## Examples

- Todo App
- Calculator
- Weather Dashboard
- Chat Interface
- E-commerce Product Card
- Login Form
- Dashboard Layout
- Data Table
- Image Gallery
- UI from Image (multimodal)