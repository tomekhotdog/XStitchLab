#!/bin/bash
# Run both backend and frontend with logging (overwrites previous logs)

cd "$(dirname "$0")"

mkdir -p logs

echo "Starting XStitchLab development servers..."
echo "Backend log: logs/backend.log"
echo "Frontend log: logs/frontend.log"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

# Clear previous logs
> logs/backend.log
> logs/frontend.log

# Start backend in background
source .venv/bin/activate
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000 >> logs/backend.log 2>&1 &
BACKEND_PID=$!

# Start frontend in background
cd frontend
npm run dev >> ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "Tailing logs (Ctrl+C to stop)..."
echo "================================"

# Cleanup on exit
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    # Kill any orphaned processes
    pkill -f "uvicorn backend.app.main:app" 2>/dev/null
    pkill -f "vite" 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Tail both logs
tail -f logs/backend.log logs/frontend.log
