# src/omni_lpr/rest.py

import logging
from pydantic import BaseModel, ValidationError
from spectree import Response, SpecTree
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from .api_models import (
    ErrorResponse,
    JsonContentBlock,
    ToolListResponse,
    ToolResponse,
)
from .tools import tool_registry

# Initialize logger
_logger = logging.getLogger(__name__)

# 1. Initialize Spectree for API documentation generation
# This instance will be used to decorate and document our endpoints.
api_spec = SpecTree(
    "starlette",
    title="Omni-LPR API",
    description="A multi-interface server for automatic license plate recognition.",
    version="1.0.0",
)


@api_spec.validate(resp=Response(HTTP_200=ToolListResponse), tags=["Tool Listing"])
async def list_tools(request: Request) -> JSONResponse:
    """
    Lists all available tools.
    """
    tools = tool_registry.list()
    # The tool definitions are TypedDicts, convert them to dicts for the response model
    tool_dicts = [dict(t) for t in tools]
    response_data = ToolListResponse(tools=tool_dicts)
    return JSONResponse(response_data.model_dump())


# 2. Define the core tool invocation endpoint logic
@api_spec.validate(
    resp=Response(
        HTTP_200=ToolResponse,
        HTTP_400=ErrorResponse,
        HTTP_404=ErrorResponse,
        HTTP_500=ErrorResponse,
    ),
    tags=["Tool Invocation"],
)
async def invoke_tool(request: Request) -> JSONResponse:
    """
    Handles the execution of a specific tool identified by its name.
    """
    tool_name = request.path_params["tool_name"]
    _logger.info(f"REST endpoint 'invoke_tool' called for tool: '{tool_name}'")

    # Check if the tool exists
    if tool_name not in tool_registry._tools:
        error = ErrorResponse(
            error={"code": "NOT_FOUND", "message": f"Tool '{tool_name}' not found."}
        )
        return JSONResponse(error.model_dump(), status_code=404)

    # Get the expected input model for this specific tool
    input_model = tool_registry._tool_models.get(tool_name, BaseModel)

    try:
        # Validate the incoming request body against the tool's specific model
        json_data = await request.json()
        validated_args = input_model(**json_data)
    except ValidationError as e:
        error = ErrorResponse(
            error={
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed.",
                "details": e.errors(),
            }
        )
        return JSONResponse(error.model_dump(), status_code=400)
    except Exception:
        error = ErrorResponse(
            error={"code": "INVALID_JSON", "message": "Request body is not valid JSON."}
        )
        return JSONResponse(error.model_dump(), status_code=400)

    try:
        # Execute the tool
        # The tool function returns MCP-style ContentBlocks
        mcp_content_blocks = await tool_registry.call(tool_name, validated_args.model_dump())

        # Convert MCP ContentBlocks to our API's JsonContentBlock
        api_content_blocks = [JsonContentBlock(data=block.text) for block in mcp_content_blocks]

        # Wrap in the final ToolResponse model
        response_data = ToolResponse(content=api_content_blocks)
        return JSONResponse(response_data.model_dump())

    except Exception as e:
        _logger.error(f"An unexpected error occurred in tool '{tool_name}': {e}", exc_info=True)
        error = ErrorResponse(
            error={"code": "INTERNAL_SERVER_ERROR", "message": "An internal server error occurred."}
        )
        return JSONResponse(error.model_dump(), status_code=500)


# 3. Create a function to set up all v1 routes
def setup_rest_routes() -> list[Route]:
    """
    Creates and decorates all REST API routes.
    """
    routes = [
        Route("/tools", endpoint=list_tools, methods=["GET"]),
        Route("/tools/{tool_name}/invoke", endpoint=invoke_tool, methods=["POST"]),
    ]

    # Note: The GET /tools endpoint can be added here as well and decorated similarly.

    return routes
