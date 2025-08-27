import logging

import anyio
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from .tools import tool_registry

_logger = logging.getLogger(__name__)

app = Server("omni-lpr")


@app.call_tool()
async def call_tool_handler(name: str, arguments: dict) -> list[types.ContentBlock]:
    _logger.debug(f"Tool call received: {name} with arguments: {arguments}")
    return await tool_registry.call(name, arguments)


@app.list_tools()
async def list_tools_handler() -> list[types.Tool]:
    _logger.debug("Tool list requested.")
    return tool_registry.list()


def run_stdio_transport(app: Server):
    async def arun():
        _logger.info("Starting stdio server.")

        async with stdio_server() as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())

    anyio.run(arun)
