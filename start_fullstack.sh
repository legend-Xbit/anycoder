#!/bin/bash
# Start both backend and frontend in separate terminal windows
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

echo "🚀 Starting AnyCoder Full-Stack Application..."
echo ""

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for required tools
if ! command_exists python3; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

if ! command_exists node; then
    echo "❌ Node.js is not installed"
    exit 1
fi

# Make scripts executable
chmod +x start_backend.sh
chmod +x start_frontend.sh

echo "📦 Starting Backend..."
# Start backend in background with venv activated
(
    if [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
        source "$SCRIPT_DIR/.venv/bin/activate"
    fi
    ANYCODER_ALLOW_DEV_AUTH=1 python backend_api.py
) &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

echo ""
echo "🎨 Starting Frontend..."
# Start frontend in background
./start_frontend.sh &
FRONTEND_PID=$!

echo ""
echo "✅ Full-stack application started!"
echo ""
echo "🔗 Backend API: http://localhost:8000"
echo "🔗 API Docs: http://localhost:8000/docs"
echo "🔗 Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both services"

# Wait for Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
