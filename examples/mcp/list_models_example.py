# File: examples/mcp/list_models_example.py

import argparse

import anyio
from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client


async def amain(url: str):
    """Connects to the MCP server and calls the list_models tool."""
    print(f"Connecting to MCP server using Streamable HTTP at {url}")

    try:
        # Fix: Unpack all three returned values, ignoring the third.
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("Client initialized.")

                tool_name = "list_models"
                print(f"Calling tool '{tool_name}'")
                result = await session.call_tool(tool_name)

                print("Response from server:")
                content_block = result.content[0]
                if isinstance(content_block, types.TextContent):
                    print(content_block.text)
                else:
                    print(result)

    except Exception as e:
        print(f"An error occurred: {e}")
        print("Please ensure the Omni-LPR server is running and accessible at the specified URL.")


def main():
    """Parses command-line arguments and runs the async main function."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        type=str,
        default="http://127.0.0.1:8000/mcp/",
        help="The URL for the endpoint.",
    )
    args = parser.parse_args()
    anyio.run(amain, args.url)


if __name__ == "__main__":
    main()
