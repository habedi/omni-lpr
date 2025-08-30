import logging

import click
from mcp.server.sse import SseServerTransport
from pythonjsonlogger import jsonlogger
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from .mcp import app
from .rest import setup_rest_routes
from .settings import update_settings
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
    _logger.debug("Health check requested.")
    return JSONResponse({"status": "ok"})


# Create app in global scope so it can be imported, but without routes.
# Routes will be added in main() after tools are set up.
starlette_app = Starlette(debug=True)


def setup_app_routes(app: Starlette):
    """Adds routes to the Starlette application."""
    app.routes.extend(
        [
            Route("/mcp/sse", endpoint=handle_sse, methods=["GET"]),
            Mount("/mcp/messages/", app=sse.handle_post_message),
            Route("/api/health", endpoint=health_check, methods=["GET"]),
            Mount("/api", routes=setup_rest_routes()),
        ]
    )


@click.command()
@click.option("--host", default="127.0.0.1", help="The host to bind to.", envvar="HOST")
@click.option("--port", default=8000, help="The port to bind to.", envvar="PORT")
@click.option("--log-level", default="INFO", help="The log level to use.", envvar="LOG_LEVEL")
@click.option(
    "--default-ocr-model",
    default="cct-xs-v1-global-model",
    help="The default OCR model to use.",
    envvar="DEFAULT_OCR_MODEL",
)
def main(host: str, port: int, log_level: str, default_ocr_model: str) -> int:
    """Main entrypoint for the omni-lpr server."""
    import uvicorn

    # First, update settings from command line/env vars
    update_settings(default_ocr_model=default_ocr_model)

    # Then, setup logging
    setup_logging(log_level)

    # Now that settings are loaded, setup the tools and their schemas
    _logger.info("Setting up tools...")
    setup_tools()

    # Now that tools are registered, add the routes to the app
    setup_app_routes(starlette_app)

    _logger.info(f"Starting SSE server on {host}:{port}")
    uvicorn.run(starlette_app, host=host, port=port)
    return 0


if __name__ == "__main__":
    main()
