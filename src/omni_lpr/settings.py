from importlib.metadata import PackageNotFoundError, version
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


def get_pkg_version() -> str:
    """Fetches the package version, falling back to '0.0.0' if not installed."""
    try:
        return version("omni-lpr")
    except PackageNotFoundError:
        return "0.0.0"


class ServerSettings(BaseSettings):
    """Server and model configuration settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    pkg_version: str = get_pkg_version()
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    max_image_size_mb: int = 5
    model_cache_size: int = 16
    execution_device: Literal["auto", "cpu", "cuda", "openvino"] = "auto"
    default_ocr_model: str = "cct-xs-v1-global-model"
    default_detector_model: str = "yolo-v9-t-384-license-plate-end2end"


# Singleton instance
settings = ServerSettings()
