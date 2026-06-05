"""
Application configuration using Pydantic Settings.

Loads configuration from YAML files and environment variables.
Environment variables override YAML values.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ---------------------------------------------------------------------------
# Project root detection
# ---------------------------------------------------------------------------
def _find_project_root() -> Path:
    """Walk upward from this file to locate the project root (contains pyproject.toml)."""
    current = Path(__file__).resolve().parent
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


PROJECT_ROOT = _find_project_root()


# ---------------------------------------------------------------------------
# Nested settings models
# ---------------------------------------------------------------------------
class ServerSettings(BaseModel):
    """HTTP server configuration."""

    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1


class ObjectDetectionSettings(BaseModel):
    """YOLO object detection model settings."""

    model_path: str = "models/weights/yolo11s.pt"
    confidence_threshold: float = 0.5
    iou_threshold: float = 0.45
    imgsz: int = 640


class MaskDetectionSettings(BaseModel):
    """Face mask detection model settings."""

    model_path: str = "models/weights/yolo11n_mask.pt"
    confidence_threshold: float = 0.5
    iou_threshold: float = 0.45
    imgsz: int = 640


class EmotionSettings(BaseModel):
    """Emotion recognition model settings."""

    model_name: str = "enet_b0_8_va_mtl"
    confidence_threshold: float = 0.4
    temporal_smoothing_alpha: float = 0.15
    temporal_window_size: int = 10


class ModelSettings(BaseModel):
    """Aggregated AI model configuration."""

    device: str = "cpu"
    object_detection: ObjectDetectionSettings = ObjectDetectionSettings()
    mask_detection: MaskDetectionSettings = MaskDetectionSettings()
    emotion_recognition: EmotionSettings = EmotionSettings()


class TrackingSettings(BaseModel):
    """Multi-object tracker configuration."""

    tracker_type: str = "bytetrack"
    track_high_thresh: float = 0.5
    track_low_thresh: float = 0.1
    new_track_thresh: float = 0.6
    track_buffer: int = 30
    match_thresh: float = 0.8


class VideoSettings(BaseModel):
    """Video pipeline configuration."""

    max_fps: int = 30
    buffer_size: int = 30
    jpeg_quality: int = 80
    resize_width: int = 640
    skip_frames: int = 1


class DatabaseSettings(BaseModel):
    """Database connection settings."""

    url: str = "sqlite+aiosqlite:///data/live_detection.db"
    pool_size: int = 20
    max_overflow: int = 10
    echo: bool = False
    batch_insert_size: int = 50
    batch_insert_interval_seconds: int = 5


class RedisSettings(BaseModel):
    """Redis connection settings."""

    url: str = "redis://localhost:6379/0"
    enabled: bool = False


class AlertSettings(BaseModel):
    """Alert engine settings."""

    enabled: bool = True
    cooldown_seconds: int = 60


class StorageSettings(BaseModel):
    """File storage settings."""

    snapshot_dir: str = "data/snapshots"
    video_clip_dir: str = "data/clips"
    retention_days: int = 30


class MonitoringSettings(BaseModel):
    """Observability settings."""

    prometheus_enabled: bool = True
    metrics_endpoint: str = "/metrics"


# ---------------------------------------------------------------------------
# Main settings class
# ---------------------------------------------------------------------------
class Settings(BaseSettings):
    """
    Root application settings.

    Priority (highest to lowest):
        1. Environment variables (prefixed with APP_)
        2. .env file
        3. YAML config file
        4. Field defaults
    """

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -- Application metadata --
    app_name: str = "Live Detection System"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    log_format: str = "console"  # 'console' or 'json'

    # -- Sub-configurations --
    server: ServerSettings = ServerSettings()
    models: ModelSettings = ModelSettings()
    tracking: TrackingSettings = TrackingSettings()
    video: VideoSettings = VideoSettings()
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    alerts: AlertSettings = AlertSettings()
    storage: StorageSettings = StorageSettings()
    monitoring: MonitoringSettings = MonitoringSettings()

    # -- Security / CORS --
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    api_key: str | None = None


# ---------------------------------------------------------------------------
# YAML config loader
# ---------------------------------------------------------------------------
def load_yaml_config(path: str | Path) -> dict[str, Any]:
    """
    Load a YAML configuration file and return its contents as a dict.

    Args:
        path: Path to the YAML file.

    Returns:
        Parsed YAML as a dictionary. Empty dict if file doesn't exist.
    """
    config_path = Path(path)
    if not config_path.exists():
        return {}
    with open(config_path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge *override* into *base*, returning a new dict."""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _flatten_yaml_to_env_style(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """
    Convert nested YAML dict keys into Pydantic-compatible flat kwargs.

    Example::

        {"server": {"host": "0.0.0.0"}}  →  {"server": ServerSettings(host="0.0.0.0")}

    For top-level scalars the key is returned as-is.
    For nested dicts we leave them as dicts so Pydantic can parse sub-models.
    """
    result: dict[str, Any] = {}
    for key, value in data.items():
        result[key] = value
    return result


# ---------------------------------------------------------------------------
# Cached settings factory
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def get_settings(config_path: str | None = None) -> Settings:
    """
    Build and cache the application settings.

    Resolution order:
        1. Load YAML from *config_path* (or ``configs/default.yaml``).
        2. Merge with environment-specific YAML (e.g. ``configs/production.yaml``)
           if ``APP_ENV`` is set.
        3. Environment variables and ``.env`` file override everything.
    """
    if config_path is None:
        config_path = os.getenv("APP_CONFIG_PATH", str(PROJECT_ROOT / "configs" / "default.yaml"))

    yaml_data = load_yaml_config(config_path)

    # Optionally merge environment-specific overlay
    app_env = os.getenv("APP_ENV", "")
    if app_env:
        env_yaml_path = PROJECT_ROOT / "configs" / f"{app_env}.yaml"
        env_data = load_yaml_config(env_yaml_path)
        yaml_data = _deep_merge(yaml_data, env_data)

    # Flatten top-level YAML sections into kwargs for Settings
    flat = _flatten_yaml_to_env_style(yaml_data)

    # Map YAML top-level keys to Settings field names
    init_kwargs: dict[str, Any] = {}
    field_mapping = {
        "app": None,  # expanded below
        "server": "server",
        "models": "models",
        "tracking": "tracking",
        "video": "video",
        "database": "database",
        "redis": "redis",
        "alerts": "alerts",
        "storage": "storage",
        "monitoring": "monitoring",
    }

    # Handle the "app" section specially
    if "app" in flat and isinstance(flat["app"], dict):
        app_section = flat["app"]
        for k, v in app_section.items():
            mapped_key = f"app_{k}" if k in ("name", "version") else k
            init_kwargs[mapped_key] = v

    for yaml_key, settings_field in field_mapping.items():
        if settings_field and yaml_key in flat:
            init_kwargs[settings_field] = flat[yaml_key]

    # Let Pydantic merge env vars on top
    return Settings(**init_kwargs)
