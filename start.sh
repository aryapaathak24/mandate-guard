#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

echo "======================================================="
echo "  🚀 Starting Agentic Guard (Track 1: Agentic Commerce)"
echo "======================================================="

# 1. Setup backend Python environment
cd "$DIR/backend"
if [ ! -d ".venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv .venv
fi

echo "📦 Installing / verifying backend dependencies..."
.venv/bin/pip install -q -r requirements.txt

echo "🧪 Running backend test suite..."
.venv/bin/pytest -q

# 2. Setup frontend
cd "$DIR/frontend"
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend npm dependencies..."
    npm install
fi

echo ""
echo "======================================================="
echo "  🌐 Launching Services on localhost"
echo "  - Backend:  http://127.0.0.1:8000"
echo "  - Frontend: http://localhost:3000"
echo "======================================================="
echo ""

# Start backend in background
cd "$DIR/backend"
.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Start frontend
cd "$DIR/frontend"
npm run dev &
FRONTEND_PID=$!

# Trap signals to clean up background processes
trap "echo 'Shutting down services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM EXIT

# Keep script running
wait
