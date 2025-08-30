import logging

import mcp.types as types
from mcp.server.lowlevel import Server

from .tools import tool_registry

_logger = logging.getLogger(__name__)

app = Server("omni-lpr")


@app.call_tool()
async def call_tool_handler(name: str, arguments: dict) -> list[types.ContentBlock]:
    """
    Handles the execution of a tool call by delegating the request to the tool registry.

    This asynchronous function processes tool call requests by identifying the tool
    by its name and providing the required arguments. The function returns the
    results of the tool execution as a list of content blocks.

    Parameters:
        name: str
            The name of the tool to be called.
        arguments: dict
            A dictionary containing the arguments required for the tool.

    Returns:
        list[types.ContentBlock]
            A list of content blocks resulting from the tool's processing.
    """
    _logger.debug(f"Tool call received: {name} with arguments: {arguments}")
    return await tool_registry.call(name, arguments)


@app.list_tools()
async def list_tools_handler() -> list[types.Tool]:
    """
    Handles the listing of tools available in the application.

    This function is responsible for responding to requests that need a
    list of registered tools. It uses the centralized tool registry to
    fetch and return the available tools in a structured manner.

    Returns:
        list[types.Tool]: A list containing the registered tools.
    """
    _logger.debug("Tool list requested.")
    return tool_registry.list()
