from click.testing import CliRunner

from omni_lpr.__main__ import main
from omni_lpr.settings import settings


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Main entrypoint for the omni-lpr server" in result.output
    assert "--host" in result.output
    assert "--port" in result.output


def test_cli_argument_overrides(mocker):
    # Save original settings to restore later
    orig_host = settings.host
    orig_port = settings.port
    orig_log_level = settings.log_level
    orig_ocr = settings.default_ocr_model
    orig_detector = settings.default_detector_model
    orig_max_size = settings.max_image_size_mb
    orig_cache_size = settings.model_cache_size

    mock_uvicorn_run = mocker.patch("uvicorn.run")
    mock_setup_logging = mocker.patch("omni_lpr.__main__.setup_logging")
    mock_setup_cache = mocker.patch("omni_lpr.__main__.setup_cache")

    try:
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "--host", "127.0.0.9",
                "--port", "9000",
                "--log-level", "DEBUG",
                "--default-ocr-model", "cct-xs-v1-global-model",
                "--default-detector-model", "yolo-v9-t-256-license-plate-end2end",
                "--max-image-size-mb", "15",
                "--model-cache-size", "10",
            ],
        )

        assert result.exit_code == 0
        assert settings.host == "127.0.0.9"
        assert settings.port == 9000
        assert settings.log_level == "DEBUG"
        assert settings.default_ocr_model == "cct-xs-v1-global-model"
        assert settings.default_detector_model == "yolo-v9-t-256-license-plate-end2end"
        assert settings.max_image_size_mb == 15
        assert settings.model_cache_size == 10

        mock_setup_logging.assert_called_once_with("DEBUG")
        mock_setup_cache.assert_called_once()
        mock_uvicorn_run.assert_called_once()

    finally:
        # Restore settings
        settings.host = orig_host
        settings.port = orig_port
        settings.log_level = orig_log_level
        settings.default_ocr_model = orig_ocr
        settings.default_detector_model = orig_detector
        settings.max_image_size_mb = orig_max_size
        settings.model_cache_size = orig_cache_size
