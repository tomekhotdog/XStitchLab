"""FastAPI app: a thin HTTP layer over `xstitchlab.library` and `xstitchlab.ops.registry`."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app import errors
from backend.app.config import settings
from backend.app.routes import designs, ops

app = FastAPI(title=settings.app_name, version="0.2.0", docs_url="/docs", redoc_url="/redoc")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

errors.install(app)
app.include_router(designs.router)
app.include_router(ops.router)


@app.get("/api/health")
def health():
    return {"status": "healthy", "app": settings.app_name}
