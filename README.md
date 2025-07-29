---
title: Anycoder
emoji: 🏢
colorFrom: indigo
colorTo: indigo
sdk: gradio
sdk_version: 5.38.2
app_file: app.py
pinned: false
disable_embedding: true
hf_oauth: true
hf_oauth_scopes:
- manage-repos
---

# AnyCoder - AI Code Generator

AnyCoder is an AI-powered code generator that helps you create applications by describing them in plain English. It supports multiple AI models, multimodal input, website redesign, and one-click deployment to Hugging Face Spaces. The UI is built with Gradio theming for a minimal, modern experience.

## Features

- **Multi-Model Support**: Choose from Moonshot Kimi-K2, DeepSeek V3, DeepSeek R1, ERNIE-4.5-VL, MiniMax M1, Qwen3-235B-A22B, SmolLM3-3B, and GLM-4.1V-9B-Thinking
- **Flexible Input**: Describe your app in text, upload a UI design image (for multimodal models), provide a reference file (PDF, TXT, MD, CSV, DOCX, or image), or enter a website URL for redesign
- **Web Search Integration**: Enable real-time web search (Tavily, with advanced search depth) to enhance code generation with up-to-date information and best practices
- **Code Generation**: Generate code in HTML, Python, JS, and more. Special support for transformers.js apps (outputs index.html, index.js, style.css)
- **Live Preview**: Instantly preview generated HTML in a sandboxed iframe
- **Modify Existing Code**: Use search/replace block format to update generated HTML
- **One-Click Deployment**: Deploy your app to Hugging Face Spaces (Gradio, Streamlit, Static HTML, or Transformers.js) with OAuth login
- **History & Examples**: Chat-like history of all interactions and quick example prompts for fast prototyping
- **Minimal, Modern UI**: Built with Gradio 5.x, using only built-in theming and styling (no custom CSS)

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
3. Describe your application in the text input field, or:
   - Upload a UI design image (for ERNIE-4.5-VL or GLM-4.1V-9B-Thinking)
   - Upload a reference file (PDF, TXT, MD, CSV, DOCX, or image)
   - Enter a website URL for redesign (the app will extract and analyze the HTML and content)
   - Enable web search for up-to-date information
   - Choose a different AI model or code language
4. Click "Generate" to create your code
5. View the generated code in the Code tab or see it in action in the Preview tab
6. Use the History tab to review previous generations
7. **Deploy to Space**: Enter a title, select SDK, and click "🚀 Deploy App" to publish your application (OAuth login required)

## Supported Models

- Moonshot Kimi-K2
- DeepSeek V3
- DeepSeek R1
- ERNIE-4.5-VL (multimodal)
- MiniMax M1
- Qwen3-235B-A22B
- SmolLM3-3B
- GLM-4.1V-9B-Thinking (multimodal)

## Input Options

- **Text Prompt**: Describe your app or code requirements
- **Image Upload**: For multimodal models, upload a UI design image to generate code from visuals
- **File Upload**: Provide a reference file (PDF, TXT, MD, CSV, DOCX, or image) for code generation or text extraction (OCR for images)
- **Website URL**: Enter a URL to extract and redesign the website (HTML and content are analyzed and modernized)

## Web Search Feature

- Enable the "Web search" toggle to use Tavily for real-time information (requires TAVILY_API_KEY)
- Uses advanced search depth for best results

## Code Generation & Modification

- Generates code in HTML, Python, JS, and more (selectable via dropdown)
- Special support for transformers.js apps (outputs index.html, index.js, style.css)
- Svelte apps
- For HTML, provides a live preview in a sandboxed iframe
- For modification requests, uses a search/replace block format to update existing HTML

## Deployment

- Deploy generated apps to Hugging Face Spaces directly from the UI
- Supported SDKs: Gradio (Python), Streamlit (Python), Static (HTML), Transformers.js
- OAuth login with Hugging Face is required for deployment to user-owned Spaces

## History & Examples

- Maintains a chat-like history of user/assistant interactions
- Quick example prompts are available in the sidebar for fast prototyping

## UI/UX

- Built with Gradio 5.x, using only Gradio's built-in theming and styling (no custom CSS)
- Minimal, uncluttered sidebar and interface

## Environment Variables

- `HF_TOKEN`: Your Hugging Face API token (required)
- `TAVILY_API_KEY`: Your Tavily API key (optional, for web search)

## Project Structure

```
anycoder/
├── app.py          # Main application (all logic and UI)
├── requirements.txt
├── README.md       # This file
```

## License

[Add your license information here]