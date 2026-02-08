#!/bin/bash
# Run frontend dev server with logging (overwrites previous log)

cd "$(dirname "$0")/frontend"

LOG_FILE="../logs/frontend.log"

echo "Starting frontend dev server..."
echo "Logs: $LOG_FILE"

# Run vite dev server, overwrite log file
exec npm run dev 2>&1 | tee "$LOG_FILE"
