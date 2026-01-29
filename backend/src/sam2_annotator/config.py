"""Application configuration."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Video directory - configurable via environment variable
    video_dir: Path = Path(os.environ.get("SAM2_VIDEO_DIR", "./videos"))

    # Checkpoint directory
    checkpoint_dir: Path = Path(os.environ.get("SAM2_CHECKPOINT_DIR", "./checkpoints"))

    # Default SAM2 model
    default_model: str = os.environ.get("SAM2_MODEL", "sam2_hiera_large")

    # Annotations output directory
    annotations_dir: Path = Path(os.environ.get("SAM2_ANNOTATIONS_DIR", "./annotations"))

    # Extracted frames cache directory
    frames_cache_dir: Path = Path(os.environ.get("SAM2_FRAMES_CACHE_DIR", "./frame_cache"))

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000

    # Frame extraction settings
    default_frame_step: int = 1  # Extract every Nth frame

    class Config:
        env_prefix = "SAM2_"


settings = Settings()

# Ensure directories exist
settings.annotations_dir.mkdir(parents=True, exist_ok=True)
settings.frames_cache_dir.mkdir(parents=True, exist_ok=True)
