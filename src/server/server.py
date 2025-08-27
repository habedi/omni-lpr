import anyio
import click
import httpx
import mcp.types as types
import picologging as logging
from mcp.server.lowlevel import Server
from mcp.shared._httpx_utils import create_mcp_http_client
from pydantic_settings import BaseSettings, SettingsConfigDict

logging.basicConfig()

_logger = logging.getLogger(__name__)


# --- Configuration Management ---
# Uses Pydantic to load settings from environment variables or a .env file.
# This centralizes configuration and makes it easier to manage in different environments.
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    port: int = 8000
    host: str = "127.0.0.1"
    transport: str = "stdio"
    log_level: str = "INFO"


# --- Logging Setup ---
def setup_logging(log_level: str):
    """Configures structured logging for the application."""
    level = logging.getLevelName(log_level.upper())
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    _logger.info(f"Logging configured with level: {log_level.upper()}")


# --- Tool Implementation ---
async def fetch_website(url: str) -> list[types.ContentBlock]:
    """
    Fetches website content with a timeout and proper error handling.
    """
    headers = {"User-Agent": "MCP Template Server (github.com/habedi/template-mcp-server)"}
    try:
        async with create_mcp_http_client(headers=headers, timeout=10.0) as client:
            _logger.info(f"Fetching URL: {url}")
            response = await client.get(url)
            response.raise_for_status()
            _logger.info(f"Successfully fetched URL: {url} with status: {response.status_code}")
            return [types.TextContent(type="text", text=response.text)]
    except httpx.HTTPStatusError as e:
        error_message = (
            f"HTTP error occurred: {e.response.status_code} - {e.response.reason_phrase}"
        )
        _logger.error(error_message)
        return [types.ErrorContent(type="error", message=error_message)]
    except httpx.RequestError as e:
        error_message = f"An error occurred while requesting {e.request.url!r}: {e}"
        _logger.error(error_message)
        return [types.ErrorContent(type="error", message=error_message)]


# --- CLI and Server Entrypoint ---
@click.command()
def main() -> int:
    """Main entrypoint to configure and run the MCP server."""
    settings = Settings()
    setup_logging(settings.log_level)

    app = Server("mcp-website-fetcher")

    @app.call_tool()
    async def fetch_tool(name: str, arguments: dict) -> list[types.ContentBlock]:
        _logger.debug(f"Tool call received: {name} with arguments: {arguments}")
        if name != "fetch":
            _logger.warning(f"Unknown tool requested: {name}")
            return [types.ErrorContent(type="error", message=f"Unknown tool: {name}")]

        url = arguments.get("url")
        if not url:
            _logger.error("Tool 'fetch' called without 'url' argument.")
            return [types.ErrorContent(type="error", message="Missing required argument 'url'")]

        return await fetch_website(url)

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        _logger.debug("Tool list requested.")
        return [
            types.Tool(
                name="fetch",
                title="Website Fetcher",
                description="Fetches a website and returns its content",
                inputSchema={
                    "type": "object",
                    "required": ["url"],
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to fetch",
                        }
                    },
                },
            )
        ]

    if settings.transport == "sse":
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse, Response
        from starlette.routing import Mount, Route

        sse = SseServerTransport("/messages/")

        async def handle_sse(request):
            async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
                await app.run(streams[0], streams[1], app.create_initialization_options())
            return Response()

        async def health_check(request):
            """A simple health check endpoint."""
            _logger.debug("Health check requested.")
            return JSONResponse({"status": "ok"})

        starlette_app = Starlette(
            debug=True,
            routes=[
                Route("/sse", endpoint=handle_sse, methods=["GET"]),
                Route("/health", endpoint=health_check, methods=["GET"]),
                Mount("/messages/", app=sse.handle_post_message),
            ],
        )

        import uvicorn

        _logger.info(f"Starting SSE server on {settings.host}:{settings.port}")
        uvicorn.run(starlette_app, host=settings.host, port=settings.port)
    else:
        from mcp.server.stdio import stdio_server

        async def arun():
            _logger.info("Starting stdio server.")
            async with stdio_server() as streams:
                await app.run(streams[0], streams[1], app.create_initialization_options())

        anyio.run(arun)

    return 0
