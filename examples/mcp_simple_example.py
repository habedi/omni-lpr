import anyio
from mcp.client.lowlevel import Client, ClientInitializationOptions
from mcp.client.sse import SseClientTransport

from shared import get_args, get_image_base64


async def amain(image_path: str, url: str):
    """Connects to the MCP server and calls a tool."""
    # Read the image file and encode it in base64
    image_base64 = get_image_base64(image_path)
    if not image_base64:
        return

    # The URL for the MCP SSE endpoint
    transport = SseClientTransport(url)

    print(f"Connecting to MCP server at {url}")

    async with Client(transport) as client:
        # Initialize the client
        await client.initialize(ClientInitializationOptions())

        print("Client initialized. Listing available tools...")
        tools = await client.list_tools()
        print("Available tools:", [tool.name for tool in tools])

        # The tool to call
        tool_name = "detect_and_recognize_plate"

        # The arguments for the tool
        tool_args = {"image_base64": image_base64}

        print(f"Calling tool '{tool_name}' with image: {image_path}")

        # Call the tool
        result = await client.call_tool(tool_name, tool_args)

        # Print the result
        print("Response from server:")
        print(result)


def main():
    """Parses command-line arguments and runs the async main function."""
    args = get_args(default_url="http://127.0.0.1:8000/mcp/sse")
    anyio.run(amain, args.image_path, args.url)


if __name__ == "__main__":
    main()
