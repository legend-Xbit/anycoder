---
title: AnyCoder
emoji: 🏆
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
disable_embedding: false
hf_oauth: true
hf_oauth_expiration_minutes: 43200
hf_oauth_scopes:
- manage-repos
- write-discussions
---


# AnyCoder - AI Code Generator with React Frontend

AnyCoder is a full-stack AI-powered code generator with a modern React/TypeScript frontend and FastAPI backend. Generate applications by describing them in plain English, with support for multiple AI models and one-click deployment to Hugging Face Spaces.

## 🎨 Features

- **Modern React UI**: Apple-inspired design with VS Code layout
- **Real-time Streaming**: Server-Sent Events for live code generation
- **Multi-Model Support**: MiniMax M2, DeepSeek V3, and more via HuggingFace InferenceClient
- **Multiple Languages**: HTML, Gradio, Streamlit, React, Transformers.js, ComfyUI
- **Authentication**: HuggingFace OAuth + Dev mode for local testing
- **One-Click Deployment**: Deploy generated apps directly to HF Spaces

## 🏗️ Architecture

```
anycoder/
├── backend_api.py           # FastAPI backend with streaming
├── frontend/                # Next.js React frontend
│   ├── src/
│   │   ├── app/            # Pages (page.tsx, layout.tsx, globals.css)
│   │   ├── components/     # React components
│   │   ├── lib/            # API client, auth utilities
│   │   └── types/          # TypeScript types
│   └── package.json
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker Space configuration
└── start_fullstack.sh      # Local development script
```

## 🚀 Quick Start

### Local Development

1. **Backend**:
```bash
export HF_TOKEN="your_huggingface_token"
export GEMINI_API_KEY="your_gemini_api_key"
python backend_api.py
```

2. **Frontend** (new terminal):
```bash
cd frontend
npm install
npm run dev
```

3. Open `http://localhost:3000`

### Using start script:
```bash
export HF_TOKEN="your_token"
export GEMINI_API_KEY="your_gemini_api_key"
./start_fullstack.sh
```

## 🐳 Docker Space Deployment

This app runs as a Docker Space on HuggingFace. The Dockerfile:
- Builds the Next.js frontend
- Runs FastAPI backend on port 7860
- Uses proper user permissions (UID 1000)
- Handles environment variables securely

## 🔑 Authentication

- **Dev Mode** (localhost): Mock login for testing
- **Production**: HuggingFace OAuth with manage-repos scope

## 📝 Supported Languages

- `html` - Static HTML pages
- `gradio` - Python Gradio apps
- `streamlit` - Python Streamlit apps
- `react` - React/Next.js apps
- `transformers.js` - Browser ML apps
- `comfyui` - ComfyUI workflows

## 🤖 Available Models

- **Gemini 3 Pro Preview** (Default) - Google's latest with deep thinking & Google Search
- MiniMax M2 (via HF router with Novita)
- DeepSeek V3/V3.1
- DeepSeek R1
- And more via HuggingFace InferenceClient

## 🎯 Usage

1. Sign in with HuggingFace (or use Dev Login locally)
2. Select a language and AI model
3. Describe your app in the chat
4. Watch code generate in real-time
5. Click **🚀 Deploy** to publish to HF Spaces

## 🛠️ Environment Variables

- `HF_TOKEN` - HuggingFace API token (required)
- `GEMINI_API_KEY` - Google Gemini API key (required for Gemini 3 Pro Preview)
- `POE_API_KEY` - Poe API key (optional, for GPT-5 and Claude models)
- `DASHSCOPE_API_KEY` - DashScope API key (optional, for Qwen models)
- `OPENROUTER_API_KEY` - OpenRouter API key (optional, for Sherlock models)
- `MISTRAL_API_KEY` - Mistral API key (optional, for Mistral models)

## 📦 Tech Stack

**Frontend:**
- Next.js 14
- TypeScript
- Tailwind CSS
- Monaco Editor

**Backend:**
- FastAPI
- HuggingFace Hub
- Server-Sent Events (SSE)

## 📄 License

MIT