import logging
from contextlib import asynccontextmanager

import click
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from pythonjsonlogger import jsonlogger
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.types import Receive, Scope, Send

from .event_store import InMemoryEventStore
from .mcp import app as mcp_app
from .settings import settings
from .tools import setup_cache, setup_tools

_logger = logging.getLogger(__name__)


def setup_logging(log_level: str):
    level = logging.getLevelName(log_level.upper())
    logHandler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    logHandler.setFormatter(formatter)
    logging.basicConfig(level=level, handlers=[logHandler])
    _logger.info(f"Logging configured with level: {log_level.upper()}")


async def health_check(_request):
    """Health check endpoint."""
    _logger.debug("Health check requested.")
    return JSONResponse({"status": "ok", "version": settings.pkg_version})


# --- Setup Streamable HTTP Manager for the main app ---
event_store = InMemoryEventStore()
session_manager = StreamableHTTPSessionManager(app=mcp_app, event_store=event_store)


async def handle_streamable_http(scope: Scope, receive: Receive, send: Send) -> None:
    """ASGI handler for streamable HTTP connections."""
    await session_manager.handle_request(scope, receive, send)


@asynccontextmanager
async def lifespan(app: Starlette):
    """Context manager for managing the session manager lifecycle."""
    async with session_manager.run():
        _logger.info("Application started with StreamableHTTP session manager.")
        try:
            yield
        finally:
            _logger.info("Application shutting down...")


# Create main app with lifespan manager
starlette_app = Starlette(debug=True, lifespan=lifespan)


def setup_app_routes(main_app: Starlette):
    """Adds routes to the Starlette application."""
    from .rest import api_spec, setup_rest_routes

    # 1. Create a separate sub-application for the documented v1 API
    api_v1_app = Starlette()
    api_v1_app.router.routes.extend(setup_rest_routes())

    # 2. Register spectree only on the sub-application
    api_spec.register(api_v1_app)

    # 3. Define other routes for the main application
    health_route = Route("/api/health", endpoint=health_check, methods=["GET"])

    # 4. Mount the sub-app and add other routes to the main app
    main_app.routes.extend(
        [
            Mount("/mcp/", app=handle_streamable_http),
            health_route,
            Mount("/api/v1", app=api_v1_app),
        ]
    )


# Run setup logic at import time
setup_tools()
setup_app_routes(starlette_app)

# Wrap the final app with CORS middleware
starlette_app = CORSMiddleware(
    starlette_app,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE"],
    expose_headers=["Mcp-Session-Id"],
)


@click.command()
@click.option("--host", default=None, help="The host to bind to.", envvar="HOST")
@click.option("--port", default=None, type=int, help="The port to bind to.", envvar="PORT")
@click.option("--log-level", default=None, help="The log level to use.", envvar="LOG_LEVEL")
# ... (the rest of the file is unchanged) ...
@click.option(
    "--default-ocr-model",
    default=None,
    help="The default OCR model to use.",
    envvar="DEFAULT_OCR_MODEL",
)
@click.option(
    "--default-detector-model",
    default=None,
    help="The default detector model to use.",
    envvar="DEFAULT_DETECTOR_MODEL",
)
@click.option(
    "--max-image-size-mb",
    default=None,
    type=int,
    help="The maximum image size in megabytes.",
    envvar="MAX_IMAGE_SIZE_MB",
)
@click.option(
    "--model-cache-size",
    default=None,
    type=int,
    help="The number of models to keep in the cache.",
    envvar="MODEL_CACHE_SIZE",
)
def main(
    host: str | None,
    port: int | None,
    log_level: str | None,
    default_ocr_model: str | None,
    default_detector_model: str | None,
    max_image_size_mb: int | None,
    model_cache_size: int | None,
) -> int:
    """Main entrypoint for the omni-lpr server."""
    import uvicorn

    # Override settings from CLI if provided
    if host:
        settings.host = host
    if port:
        settings.port = port
    if log_level:
        settings.log_level = log_level
    if default_ocr_model:
        settings.default_ocr_model = default_ocr_model
    if default_detector_model:
        settings.default_detector_model = default_detector_model
    if max_image_size_mb:
        settings.max_image_size_mb = max_image_size_mb
    if model_cache_size:
        settings.model_cache_size = model_cache_size

    setup_logging(settings.log_level)
    _logger.info("Setting up cache...")
    setup_cache()

    _logger.info(f"Starting Streamable HTTP server on {settings.host}:{settings.port}")
    uvicorn.run(starlette_app, host=settings.host, port=settings.port)
    return 0


if __name__ == "__main__":
    main()
