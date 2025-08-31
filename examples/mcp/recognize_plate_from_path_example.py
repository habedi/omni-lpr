import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anyio
from mcp import ClientSession, types
from mcp.client.sse import sse_client
from shared import get_args


async def amain(image_path: str, url: str):
    """Connects to the MCP server and calls the recognize_plate_from_path tool."""
    print(f"Connecting to MCP server using SSE at {url}")

    try:
        # Use the sse_client to get read/write streams over a Server-Sent Events connection
        async with sse_client(url) as (read, write):
            # Create a session using the streams
            async with ClientSession(read, write) as session:
                # Initialize the connection
                await session.initialize()

                print("Client initialized.")

                # The tool to call
                tool_name = "recognize_plate_from_path"

                # The arguments for the tool
                # This tool takes a file path or URL directly.
                tool_args = {"path": image_path}

                print(f"Calling tool '{tool_name}' with image path: {image_path}")

                # Call the tool
                result = await session.call_tool(tool_name, arguments=tool_args)

                # Print the result from the response structure
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
    args = get_args(default_url="http://127.0.0.1:8000/mcp/sse")
    anyio.run(amain, args.image_path, args.url)


if __name__ == "__main__":
    main()
