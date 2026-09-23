#!/bin/bash
# Start the FastAPI backend
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

echo "Starting AnyCoder FastAPI Backend..."
echo "API will be available at: http://localhost:8000"
echo "API docs at: http://localhost:8000/docs"
echo ""

# Check if HF_TOKEN is set
if [ -z "$HF_TOKEN" ]; then
    echo "⚠️  WARNING: HF_TOKEN environment variable is not set!"
    echo "Please set it with: export HF_TOKEN=your_token_here"
    echo ""
fi

# Activate the repository's virtual environment when present
if [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
fi

# Start the backend
export ANYCODER_ALLOW_DEV_AUTH=1
python backend_api.py
