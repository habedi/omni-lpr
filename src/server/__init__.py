import picologging as logging

logging.basicConfig()

from importlib.metadata import PackageNotFoundError, version

from .server import main

_logger = logging.getLogger(__name__)

try:
    __version__ = version("template-mcp-server")
except PackageNotFoundError:
    __version__ = "0.0.0-unknown"
    _logger.warning(
        "Could not determine package version using importlib.metadata. "
        "Is the library installed correctly?"
    )

__all__ = [main]
