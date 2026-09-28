#!/bin/bash
# Run the backend server with logging (overwrites the previous log)

cd "$(dirname "$0")"

mkdir -p logs
LOG_FILE="logs/backend.log"

echo "Starting backend server..."
echo "Logs: $LOG_FILE"

exec uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000 2>&1 | tee "$LOG_FILE"
