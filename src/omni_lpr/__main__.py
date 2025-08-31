import logging

import click
from mcp.server.sse import SseServerTransport
from pythonjsonlogger import jsonlogger
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from .mcp import app
from .settings import settings
from .tools import setup_tools

_logger = logging.getLogger(__name__)


def setup_logging(log_level: str):
    level = logging.getLevelName(log_level.upper())
    logHandler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    logHandler.setFormatter(formatter)
    logging.basicConfig(level=level, handlers=[logHandler])
    _logger.info(f"Logging configured with level: {log_level.upper()}")


sse = SseServerTransport("/mcp/messages/")


async def handle_sse(request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())
    return Response()


async def health_check(_request):
    """
    Health check endpoint.
    Returns the status of the server and the server version.
    """
    _logger.debug("Health check requested.")
    return JSONResponse({"status": "ok", "version": settings.pkg_version})


# Create app in global scope so it can be imported, but without routes.
# Routes will be added in main() after tools are set up.
starlette_app = Starlette(debug=True)


def setup_app_routes(app: Starlette):
    """Adds routes to the Starlette application."""
    from .rest import api_spec, setup_rest_routes

    # The /api/health endpoint can now be documented as well if desired
    health_route = Route("/api/health", endpoint=health_check, methods=["GET"])

    app.routes.extend(
        [
            Route("/mcp/sse", endpoint=handle_sse, methods=["GET"]),
            Mount("/mcp/messages/", app=sse.handle_post_message),
            health_route,
            # Mount all the new, documented v1 API routes under /api/v1
            Mount("/api/v1", routes=setup_rest_routes()),
        ]
    )
    # Register the Spectree documentation generator with the app
    api_spec.register(app)


# --- FIX: Run setup logic at import time ---
# This ensures that when Gunicorn imports `starlette_app`, it is already
# fully configured with its tools and routes.
setup_tools()
setup_app_routes(starlette_app)


# --- END FIX ---


@click.command()
@click.option("--host", default=None, help="The host to bind to.", envvar="HOST")
@click.option("--port", default=None, type=int, help="The port to bind to.", envvar="PORT")
@click.option("--log-level", default=None, help="The log level to use.", envvar="LOG_LEVEL")
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
def main(
    host: str | None,
    port: int | None,
    log_level: str | None,
    default_ocr_model: str | None,
    default_detector_model: str | None,
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

    # Then, setup logging for the CLI runner
    setup_logging(settings.log_level)

    _logger.info("Setting up tools...")
    # The setup calls were moved to the global scope and are no longer needed here.

    _logger.info(f"Starting SSE server on {settings.host}:{settings.port}")
    uvicorn.run(starlette_app, host=settings.host, port=settings.port)
    return 0


if __name__ == "__main__":
    main()
