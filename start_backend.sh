#!/bin/bash
# Start the FastAPI backend

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

# Activate virtual environment
source /Users/ahsenkhaliq/anycoder/.venv/bin/activate

# Start the backend
python backend_api.py

