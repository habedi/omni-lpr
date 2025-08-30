import logging

logging.basicConfig()

from importlib.metadata import PackageNotFoundError, version

from .__main__ import main, starlette_app

_logger = logging.getLogger(__name__)

try:
    __version__ = version("omni-lpr")
except PackageNotFoundError:
    __version__ = "0.0.0-unknown"
    _logger.warning(
        "Could not determine package version using importlib.metadata. "
        "Is the library installed correctly?"
    )

__all__ = ["main", "starlette_app"]
