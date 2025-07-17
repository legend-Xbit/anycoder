---
title: Anycoder
emoji: 🏢
colorFrom: indigo
colorTo: indigo
sdk: gradio
sdk_version: 5.38.0
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
- **Website Redesign**: Enter a website URL to extract content and redesign it with modern, responsive layouts
- **Live Preview**: See your generated code in action with the built-in sandbox
- **Web Search Integration**: Enable real-time web search to get the latest information and best practices
- **Chat History**: Keep track of your conversations and generated code
- **Quick Examples**: Pre-built examples to get you started quickly
- **🚀 One-Click Deployment**: Deploy your generated applications directly to Hugging Face Spaces

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

7. **Deploy to Space**: Enter a title and click "🚀 Deploy to Space" to publish your application

## 🚀 Deployment Feature

AnyCoder now includes one-click deployment to Hugging Face Spaces! This feature allows you to:

### How to Deploy

1. **Login**: Click the "Sign in with Hugging Face" button in the sidebar
2. **Authorize Permissions**: When the authorization page appears, make sure to grant ALL the requested permissions:
   - ✅ **read-repos** - Read access to repositories
   - ✅ **write-repos** - Write access to create repositories
   - ✅ **manage-repos** - Manage repository settings
3. **Complete Authorization**: Click "Authorize" to complete the login
4. **Generate Code**: Generate some HTML code using the AI
5. **Enter Title**: In the sidebar, enter a title for your space (e.g., "My Todo App")
6. **Deploy**: Click the "🚀 Deploy to Space" button
7. **Share**: Get a shareable URL for your deployed application

**Important**: You must grant ALL three permissions during the OAuth authorization process. If you only grant partial permissions, deployment will fail.

**Note**: You need to be logged in with your Hugging Face account to deploy. This ensures that:
- Deployments are created under your own account namespace
- You can manage and update your spaces from your Hugging Face dashboard
- Each deployment gets a unique URL under your username

**Technical Note**: The deployment uses your personal OAuth token to create spaces under your account, ensuring full security and ownership of your deployed applications.

### Troubleshooting Deployment Issues

If you encounter permission errors during deployment:

1. **Check Permissions**: Make sure you granted all three required permissions during login
2. **Logout and Login Again**: Click logout and sign in again, ensuring all permissions are granted
3. **Account Status**: Verify your Hugging Face account allows repository creation
4. **Network Issues**: Check your internet connection and try again
5. **Contact Support**: If issues persist, contact Hugging Face support

### What Gets Deployed

- **Complete HTML Application**: Your generated code wrapped in a professional template
- **Responsive Design**: Mobile-friendly layout with modern styling
- **Project Documentation**: README with project details and prompts used
- **Live URL**: Publicly accessible URL that anyone can visit

### Deployment Benefits

- **Instant Publishing**: No need to set up hosting or domains
- **Shareable**: Get a public URL to share with others
- **Professional**: Clean, branded presentation of your work
- **Version Control**: Each deployment creates a new space with timestamp
- **Free Hosting**: Hosted on Hugging Face's infrastructure

### Example Deployment

```
Title: "My Weather Dashboard"
Generated Code: <div>Weather app HTML...</div>
Result: https://huggingface.co/spaces/my-weather-dashboard-1234567890
```

The deployed space will include:
- Your application with professional styling
- A header with your title and AnyCoder branding
- A footer with attribution
- A README documenting the project

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

## Website Redesign Feature

The website redesign feature allows you to extract content from existing websites and generate modern, responsive redesigns. This feature:

1. **Extracts Website Content**: Automatically scrapes the target website to extract:
   - Page title and meta description
   - Navigation menu structure
   - Main content sections
   - Images and their descriptions
   - Overall page structure and purpose

2. **Generates Modern Redesigns**: Creates improved versions with:
   - Modern, responsive layouts
   - Enhanced user experience
   - Better accessibility
   - Mobile-first design principles
   - Current design trends and best practices

### How to Use Website Redesign

1. **Enter a Website URL**: In the "🌐 Website URL (for redesign)" field, enter the URL of the website you want to redesign
   - Example: `https://example.com`
   - The URL can be with or without `https://`

2. **Add Custom Requirements**: Optionally describe specific improvements you want:
   - "Make it more modern and minimalist"
   - "Add a dark mode toggle"
   - "Improve the mobile layout"
   - "Use a different color scheme"

3. **Enable Web Search**: Toggle the web search feature to get the latest design trends and best practices

4. **Generate**: Click "Generate" to create your redesigned website

### Example Usage

```
URL: https://example.com
Description: Redesign this website with a modern, minimalist approach. Use a clean typography and improve the mobile experience.
```

The AI will analyze the original website content and create a completely redesigned version that maintains the core functionality while providing a better user experience.

### Supported Websites

The feature works with most public websites, including:
- Business websites
- Portfolio sites
- Blog platforms
- E-commerce sites
- Landing pages
- Documentation sites

**Note**: Some websites may block automated access or require JavaScript to load content. In such cases, the extraction may be limited.

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