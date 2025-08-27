from dataclasses import dataclass


@dataclass
class ServerSettings:
    default_ocr_model: str = "cct-xs-v1-global-model"


# Singleton instance
settings = ServerSettings()


def update_settings(default_ocr_model: str):
    settings.default_ocr_model = default_ocr_model
