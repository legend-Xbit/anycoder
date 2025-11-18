#!/bin/bash
# Start the Next.js frontend

echo "Starting AnyCoder Frontend..."
echo "Frontend will be available at: http://localhost:3000"
echo ""

cd frontend

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Start the development server
npm run dev

