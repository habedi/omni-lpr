#!/usr/bin/env python3
"""
A simple, interactive MCP client that connects to the server via stdio,
using a class-based structure for better organization and resource management.
"""

import asyncio
import json
from contextlib import AsyncExitStack
from typing import Any

import anyio
import picologging as logging
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class Server:
    """Manages the connection and interaction with a single MCP server."""

    def __init__(self, command: list[str]):
        """Initializes the server configuration."""
        self.command = command
        self.session: ClientSession | None = None
        self._exit_stack = AsyncExitStack()

    async def connect(self) -> None:
        """Establishes a connection to the server and initializes a session."""
        logging.info("Connecting to server...")
        params = StdioServerParameters(command=self.command[0], args=self.command[1:], env={})
        try:
            # Enter the stdio_client context
            reader, writer = await self._exit_stack.enter_async_context(stdio_client(params))
            # Enter the ClientSession context
            self.session = await self._exit_stack.enter_async_context(ClientSession(reader, writer))
            await self.session.initialize()
            logging.info("Connection successful!")
        except Exception as e:
            logging.error(f"Failed to connect to server: {e}")
            await self.disconnect()  # Clean up on failure
            raise

    async def disconnect(self) -> None:
        """Disconnects from the server and cleans up resources."""
        logging.info("Disconnecting from server...")
        await self._exit_stack.aclose()
        self.session = None

    async def list_tools(self) -> None:
        """Lists all available tools from the server."""
        if not self.session:
            print("Not connected.")
            return

        try:
            result = await self.session.list_tools()
            if hasattr(result, "tools") and result.tools:
                print("\nAvailable tools:")
                for tool in result.tools:
                    print(f"- {tool.name}: {tool.description or 'No description'}")
                print()
            else:
                print("No tools available.")
        except Exception as e:
            print(f"Failed to list tools: {e}")

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> None:
        """Calls a specific tool on the server and prints the result."""
        if not self.session:
            print("Not connected.")
            return

        print(f"\nCalling '{tool_name}'...")
        try:
            # The call_tool method is now awaited directly.
            result = await self.session.call_tool(tool_name, arguments)
            if isinstance(result, CallToolResult):
                print("Result:")
                for block in result.content:
                    if block.type == "text":
                        print(block.text)
                    else:
                        print(block)
        except Exception as e:
            print(f"An error occurred during the tool call: {e}")


async def interactive_loop(server: Server) -> None:
    """Runs the main interactive command loop for the client."""
    print("\nSimple MCP Client")
    print("Commands: list, call <tool_name> [json_args], quit\n")
    while True:
        try:
            command_str = await anyio.to_thread.run_sync(input, "mcp> ")
            command_str = command_str.strip()
            if not command_str:
                continue

            if command_str == "quit":
                print("Goodbye!")
                break
            elif command_str == "list":
                await server.list_tools()
            elif command_str.startswith("call "):
                await handle_call_tool(server, command_str)
            else:
                print("Unknown command.")
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break


async def handle_call_tool(server: Server, command_str: str) -> None:
    """Parses and executes a 'call' command."""
    parts = command_str.split(maxsplit=2)
    tool_name = parts[1] if len(parts) > 1 else ""
    if not tool_name:
        print("Please specify a tool name.")
        return

    args_str = parts[2] if len(parts) > 2 else "{}"
    try:
        arguments = json.loads(args_str)
        await server.call_tool(tool_name, arguments)
    except json.JSONDecodeError:
        print("Invalid arguments format (expected JSON).")
    except Exception as e:
        print(f"Failed to call tool '{tool_name}': {e}")


async def main() -> None:
    """Initializes the server and runs the interactive session."""
    server_command = ["poetry", "run", "mcp-server"]
    server = Server(command=server_command)

    try:
        await server.connect()
        await interactive_loop(server)
    except Exception as e:
        logging.error(f"An error occurred in the main session: {e}")
    finally:
        await server.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nClient shutdown.")
