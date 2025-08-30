import anyio
from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client

from shared import get_args, get_image_base64


async def amain(image_path: str, url: str):
    """Connects to the MCP server using the new ClientSession API and calls a tool."""
    # Read the image file and encode it in base64
    image_base64 = get_image_base64(image_path)
    if not image_base64:
        return

    print(f"Connecting to MCP server at {url}")

    try:
        # Use the new streamablehttp_client to get read/write streams
        async with streamablehttp_client(url) as (read, write, _):
            # Create a session using the streams
            async with ClientSession(read, write) as session:
                # Initialize the connection
                await session.initialize()

                print("Client initialized. Listing available tools...")
                tools_response = await session.list_tools()
                print("Available tools:", [tool.name for tool in tools_response.tools])

                # The tool to call
                tool_name = "detect_and_recognize_plate"

                # The arguments for the tool
                tool_args = {"image_base64": image_base64}

                print(f"Calling tool '{tool_name}' with image: {image_path}")

                # Call the tool
                result = await session.call_tool(tool_name, arguments=tool_args)

                # Print the result from the new response structure
                print("Response from server:")
                content_block = result.content[0]
                if isinstance(content_block, types.TextContent):
                    print(content_block.text)
                else:
                    print(result)

    except Exception as e:
        print(f"An error occurred: {e}")
        print(
            "Note: This client requires the server to be updated to use the latest MCP streamable HTTP transport."
        )


def main():
    """Parses command-line arguments and runs the async main function."""
    args = get_args(default_url="http://127.0.0.1:8000/mcp/sse")
    anyio.run(amain, args.image_path, args.url)


if __name__ == "__main__":
    main()
