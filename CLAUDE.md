# XStitchLab

Cross-stitch pattern design tool: image → pixelation → DMC colour mapping → pattern editor → export.

## Running the app

```bash
# Start both backend (FastAPI) and frontend (Vite) together:
./run-dev.sh

# Or run individually:
./run-backend.sh   # Backend on http://localhost:8000
./run-frontend.sh  # Frontend on http://localhost:5173
```

API docs available at http://localhost:8000/docs when backend is running.

## Project structure

- **`xstitchlab/`** — Core Python package (image processing, pixelation, DMC mapping, thread calc, export)
- **`backend/`** — FastAPI server exposing the pipeline as REST endpoints (port 8000)
- **`frontend/`** — Vite browser-based pattern editor (port 5173)
- **`designs/`** — Design JSON files and outputs
- **`tests/`** — Python tests
- **`website/`** — Static marketing site

## Tech stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn, uv for package management
- **Frontend**: Vite (vanilla JS)
- **Key libs**: Pillow, NumPy, scikit-learn, colormath, fpdf2

## Tests

```bash
uv run pytest tests/ backend/tests -v
cd frontend && npm test && npm run e2e
```

## CLI

```bash
uv run xstitch convert image.png --size 40 --colors 8
uv run xstitch run designs/02-holstentor-lubeck        # run the design's saved recipe
uv run xstitch export designs/02-holstentor-lubeck --kind sheet
uv run xstitch benchmark                               # score recipes against the five finals
uv run xstitch estimate pattern.json --fabric 14
```
