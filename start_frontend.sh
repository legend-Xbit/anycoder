#!/bin/bash
# Start the Next.js frontend
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting AnyCoder Frontend..."
echo "Frontend will be available at: http://localhost:3000"
echo ""

cd "$SCRIPT_DIR/frontend" || exit 1

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Start the development server
npm run dev
