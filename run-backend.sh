#!/bin/bash
# Run backend server with logging (overwrites previous log)

cd "$(dirname "$0")"

LOG_FILE="logs/backend.log"

echo "Starting backend server..."
echo "Logs: $LOG_FILE"

# Activate venv and run uvicorn, overwrite log file
source .venv/bin/activate
exec uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000 2>&1 | tee "$LOG_FILE"
