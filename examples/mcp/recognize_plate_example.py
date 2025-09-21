# File: examples/mcp/recognize_plate_example.py

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anyio
from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client
from shared import get_args, get_image_base64


async def amain(image_path: str, url: str):
    """Connects to the MCP server and calls the recognize_plate tool."""
    image_base64 = get_image_base64(image_path)
    if not image_base64:
        return

    print(f"Connecting to MCP server using Streamable HTTP at {url}")

    try:
        # Fix: Unpack all three returned values, ignoring the third.
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("Client initialized.")

                tool_name = "recognize_plate"
                tool_args = {"image_base64": image_base64}

                print(f"Calling tool '{tool_name}' with image: {image_path}")
                result = await session.call_tool(tool_name, arguments=tool_args)

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
    args = get_args(default_url="http://127.0.0.1:8000/mcp/")
    anyio.run(amain, args.image_path, args.url)


if __name__ == "__main__":
    main()
