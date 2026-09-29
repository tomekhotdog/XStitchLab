#!/bin/bash
# Run backend (http://localhost:8000) and frontend (http://localhost:5173) together.
# Logs go to logs/backend.log and logs/frontend.log (overwritten each run). Ctrl+C stops both.

cd "$(dirname "$0")"

mkdir -p logs
: > logs/backend.log
: > logs/frontend.log

echo "Starting XStitchLab development servers..."
echo "Backend:  http://localhost:8000  (log: logs/backend.log)"
echo "Frontend: http://localhost:5173  (log: logs/frontend.log)"
echo ""

uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000 >> logs/backend.log 2>&1 &
BACKEND_PID=$!

(cd frontend && exec npm run dev >> ../logs/frontend.log 2>&1) &
FRONTEND_PID=$!

# Kill a process and all its descendants (uv -> uvicorn -> reloader worker, npm -> vite),
# and nothing else: other uvicorn/vite processes on this machine are left alone.
kill_tree() {
    local child
    for child in $(pgrep -P "$1"); do
        kill_tree "$child"
    done
    kill "$1" 2>/dev/null
}

cleanup() {
    trap - SIGINT SIGTERM EXIT
    echo ""
    echo "Stopping servers..."
    kill_tree "$BACKEND_PID"
    kill_tree "$FRONTEND_PID"
    [ -n "$TAIL_PID" ] && kill "$TAIL_PID" 2>/dev/null
    wait 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

echo "Backend PID: $BACKEND_PID, frontend PID: $FRONTEND_PID"
echo "Tailing logs (Ctrl+C to stop both servers)..."
echo "================================"

tail -f logs/backend.log logs/frontend.log &
TAIL_PID=$!
wait "$TAIL_PID"
