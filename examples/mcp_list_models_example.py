import anyio
from mcp import ClientSession, types
from mcp.client.sse import sse_client

import argparse

async def amain(url: str):
    """Connects to the MCP server and calls the list_models tool."""
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
                tool_name = "list_models"

                print(f"Calling tool '{tool_name}'")

                # Call the tool
                result = await session.call_tool(tool_name)

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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        type=str,
        default="http://127.0.0.1:8000/mcp/sse",
        help="The URL for the endpoint.",
    )
    args = parser.parse_args()
    anyio.run(amain, args.url)


if __name__ == "__main__":
    main()
