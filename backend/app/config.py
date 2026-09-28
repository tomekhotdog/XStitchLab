"""Settings from the environment: `XSTITCH_DESIGNS_DIR` overrides the library root."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from xstitchlab.library import default_root


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="XSTITCH_")

    app_name: str = "XStitchLab API"
    designs_dir: Path | None = None
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


settings = Settings()


def root() -> Path:
    """The design library root: `XSTITCH_DESIGNS_DIR`, else `<repo>/designs`."""
    return settings.designs_dir or default_root()
