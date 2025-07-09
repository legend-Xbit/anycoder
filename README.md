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

# AnyCoder - AI Code Generator

AnyCoder is an AI-powered code generator that helps you create applications by describing them in plain English. It supports multiple AI models and can generate HTML/CSS/JavaScript code for web applications.

## Features

- **Multi-Model Support**: Choose from various AI models including DeepSeek, ERNIE-4.5-VL, MiniMax, and Qwen
- **Image-to-Code**: Upload UI design images and get corresponding HTML/CSS code (ERNIE-4.5-VL model)
- **Image Text Extraction**: Upload images and extract text using OCR for processing
- **Live Preview**: See your generated code in action with the built-in sandbox
- **Web Search Integration**: Enable real-time web search to get the latest information and best practices
- **Chat History**: Keep track of your conversations and generated code
- **Quick Examples**: Pre-built examples to get you started quickly

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd anycoder
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
export HF_TOKEN="your_huggingface_token"
export TAVILY_API_KEY="your_tavily_api_key"  # Optional, for web search feature
```

## Usage

1. Run the application:
```bash
python app.py
```

2. Open your browser and navigate to the provided URL

3. Describe your application in the text input field

4. Optionally:
   - Upload a UI design image (for ERNIE-4.5-VL model)
   - Enable web search to get the latest information
   - Choose a different AI model

5. Click "Generate" to create your code

6. View the generated code in the Code Editor tab or see it in action in the Live Preview tab

## Web Search Feature

The web search feature uses Tavily to provide real-time information when generating code. To enable this feature:

1. Get a free Tavily API key from [Tavily Platform](https://tavily.com/)
2. Set the `TAVILY_API_KEY` environment variable
3. Toggle the "🔍 Enable Web Search" checkbox in the sidebar

When enabled, the AI will search the web for the latest information, best practices, and technologies related to your request.

## Image Text Extraction

The application supports extracting text from images using OCR (Optical Character Recognition). This feature allows you to:

1. Upload image files (JPG, PNG, BMP, TIFF, GIF, WebP) through the file input
2. Automatically extract text from the images using Tesseract OCR
3. Include the extracted text in your prompts for code generation

### Setting up OCR

To use the image text extraction feature, you need to install Tesseract OCR on your system. See `install_tesseract.md` for detailed installation instructions.

**Example usage:**
- Upload an image containing text (like a screenshot, document, or handwritten notes)
- The application will extract the text and include it in your prompt
- You can then ask the AI to process, summarize, or work with the extracted text

## Available Models

- **DeepSeek V3**: Advanced code generation model
- **DeepSeek R1**: Specialized for code generation tasks
- **ERNIE-4.5-VL**: Multimodal model with image support
- **MiniMax M1**: General-purpose AI model
- **Qwen3-235B-A22B**: Large language model for code generation

## Environment Variables

- `HF_TOKEN`: Your Hugging Face API token (required)
- `TAVILY_API_KEY`: Your Tavily API key (optional, for web search)

## License

[Add your license information here]

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
   export HF_TOKEN="your_huggingface_token"
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
export HF_TOKEN="your_huggingface_token"
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