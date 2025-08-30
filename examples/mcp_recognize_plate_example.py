import anyio
from mcp import ClientSession, types
from mcp.client.sse import sse_client

from shared import get_args, get_image_base64


async def amain(image_path: str, url: str):
    """Connects to the MCP server and calls the recognize_plate tool."""
    # Read the image file and encode it in base64
    image_base64 = get_image_base64(image_path)
    if not image_base64:
        return

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
                tool_name = "recognize_plate"

                # The arguments for the tool
                tool_args = {"image_base64": image_base64}

                print(f"Calling tool '{tool_name}' with image: {image_path}")

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
