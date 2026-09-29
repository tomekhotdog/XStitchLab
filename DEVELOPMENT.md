# XStitchLab Development Guide

## Setup

The repo is iCloud-synced, so the virtualenv lives in `.venv.nosync` (iCloud
skips `*.nosync`) with `.venv` as a symlink to it. Never delete or recreate
either; `uv` uses the symlink transparently.

```bash
uv sync --all-packages   # installs xstitchlab, the backend (a uv workspace member), and dev deps
cd frontend && npm install
```

## Quick Start

### Run Both Servers
```bash
./run-dev.sh
```
This starts both backend and frontend, tails both logs. Press `Ctrl+C` to stop all servers.

### Run Separately
```bash
# Terminal 1 - Backend
./run-backend.sh          # = uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 - Frontend
./run-frontend.sh
```

### Design library location

The backend serves the DesignFolders under `<repo>/designs` by default. Point it
elsewhere with `XSTITCH_DESIGNS_DIR` (the CLI's `default_root()` reads the same
variable):

```bash
XSTITCH_DESIGNS_DIR=/path/to/designs ./run-backend.sh
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
uv run pytest tests/ backend/tests -q                      # core + backend
uv run pytest tests/ -q --deselect tests/test_benchmark.py  # core without the slow benchmark
uv run pytest backend/tests -q                             # backend only (TestClient over a temp library)
```

The backend tests seed a temporary library with `designs/01-three-brothers-riga`
and override the root dependency, so they never touch `designs/`.

### Frontend

```bash
cd frontend
npm run dev        # Vite dev server on :5173 (proxies /api to BACKEND_PORT, default 8000)
npm test           # Vitest unit tests (jsdom), once
npm run test:watch # Vitest in watch mode
npm run build      # type-check (tsc --noEmit) + production build
npm run e2e        # Playwright smoke test (Chromium)
```

`npm run e2e` starts its own servers — the backend on :8001 and Vite on :5174 — so it runs
alongside `./run-dev.sh`. `e2e/global-setup.ts` copies `designs/01-three-brothers-riga` into
`frontend/e2e/.tmp-designs/` (git-ignored, wiped each run) and the backend serves that via
`XSTITCH_DESIGNS_DIR`, so the test's save never touches `designs/`. Playwright's Chromium lives in
`~/Library/Caches/ms-playwright`; after bumping `@playwright/test`, run `npx playwright install chromium`.

## Troubleshooting

### Port Already in Use
```bash
# Kill processes on specific ports
lsof -ti:8000 | xargs kill -9  # Backend
lsof -ti:5173 | xargs kill -9  # Frontend

# Or kill by process name (also stops any other uvicorn/vite, e.g. a running e2e test)
pkill -f "uvicorn backend.app.main:app"
pkill -f "vite"
```
