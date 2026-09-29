#!/bin/bash
# Run the frontend dev server (http://localhost:5173; /api is proxied to the backend on 8000).
# Log: logs/frontend.log (overwritten each run).

cd "$(dirname "$0")"

mkdir -p logs
LOG_FILE="$PWD/logs/frontend.log"

echo "Starting frontend dev server..."
echo "Logs: $LOG_FILE"

cd frontend
npm run dev 2>&1 | tee "$LOG_FILE"
