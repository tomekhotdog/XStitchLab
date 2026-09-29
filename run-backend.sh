#!/bin/bash
# Run the backend (http://localhost:8000, API docs at /docs) with auto-reload.
# Log: logs/backend.log (overwritten each run).

cd "$(dirname "$0")"

mkdir -p logs
LOG_FILE="logs/backend.log"

echo "Starting backend server..."
echo "Logs: $LOG_FILE"

uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000 2>&1 | tee "$LOG_FILE"
