# XStitchLab Development Guide

## Quick Start

### Run Both Servers
```bash
./run-dev.sh
```
This starts both backend and frontend, tails both logs. Press `Ctrl+C` to stop all servers.

### Run Separately
```bash
# Terminal 1 - Backend
./run-backend.sh

# Terminal 2 - Frontend
./run-frontend.sh
```

## Log Files

Logs are stored in the `logs/` directory and **overwritten on each run**:

| File | Description |
|------|-------------|
| `logs/backend.log` | FastAPI/Uvicorn server output |
| `logs/frontend.log` | Vite dev server output |

### Viewing Logs
```bash
# View full log
cat logs/backend.log

# Follow log in real-time
tail -f logs/backend.log

# Follow both logs
tail -f logs/backend.log logs/frontend.log
```

## Server URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000/api |
| API Docs | http://localhost:8000/docs |

## Running Tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

## Troubleshooting

### Port Already in Use
```bash
# Kill processes on specific ports
lsof -ti:8000 | xargs kill -9  # Backend
lsof -ti:5173 | xargs kill -9  # Frontend

# Or kill by process name
pkill -f "uvicorn"
pkill -f "vite"
```
