from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    default_ocr_model: str = "cct-xs-v1-global-model"
    default_detector_model: str = "yolo-v9-t-384-license-plate-end2end"


# Singleton instance
settings = ServerSettings()
