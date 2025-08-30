import json
import logging

from mcp import types
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from .errors import ErrorCode
from .tools import tool_registry

_logger = logging.getLogger(__name__)


async def list_tools_endpoint(_: Request) -> JSONResponse:
    """REST endpoint to list available tools."""
    _logger.info("REST endpoint 'list_tools' called.")
    tools_info = [
        {
            "name": tool.name,
            "title": tool.title,
            "description": tool.description,
            "input_schema": tool.inputSchema,
        }
        for tool in tool_registry.list()
    ]
    return JSONResponse({"tools": tools_info})


async def tool_invocation_endpoint(request: Request) -> JSONResponse:
    """A single, parameterized endpoint for executing any tool."""
    tool_name = request.path_params["tool_name"]
    _logger.info(f"REST endpoint for tool '{tool_name}' invoked.")

    if tool_name not in tool_registry._tools:
        _logger.warning(f"Attempted to invoke non-existent tool: {tool_name}")
        error_response = {
            "error": {
                "code": "NOT_FOUND",
                "message": f"Tool '{tool_name}' not found.",
            }
        }
        return JSONResponse(error_response, status_code=404)

    try:
        json_data = await request.json()
    except json.JSONDecodeError:
        body = await request.body()
        if not body:
            json_data = {}
        else:
            _logger.warning(f"Invalid JSON received for tool '{tool_name}'.")
            error_response = {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid JSON in request body.",
                }
            }
            return JSONResponse(error_response, status_code=400)

    model = tool_registry._tool_models[tool_name]
    try:
        validated_args = model(**json_data)
    except ValidationError as e:
        _logger.warning(f"Input validation failed for tool '{tool_name}': {e}")
        error_response = {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed.",
                "details": e.errors(),
            }
        }
        return JSONResponse(error_response, status_code=400)

    try:
        result_content: list[types.ContentBlock] = await tool_registry.call(
            tool_name, validated_args.model_dump()
        )

        # The result from the tool is a list of ContentBlock objects.
        # We need to serialize them to a JSON-compatible format.
        results_data = []
        for item in result_content:
            if isinstance(item, types.TextContent):
                if not item.text:
                    continue  # Skip empty text content
                try:
                    # The tool returns a JSON string, so we parse it
                    results_data.append(json.loads(item.text))
                except json.JSONDecodeError:
                    # If it's not a JSON string, wrap it as a simple text response
                    _logger.warning(
                        f"Tool '{tool_name}' produced non-JSON text output. Wrapping it."
                    )
                    results_data.append({"text": item.text})
            else:
                results_data.append(item.model_dump())

        # Wrap the final result in the specified 'content' structure
        response_body = {"content": [{"type": "json", "data": results_data}]}
        return JSONResponse(response_body)

    except Exception as e:
        _logger.error(f"An unexpected error occurred in tool '{tool_name}': {e}", exc_info=True)
        error_response = {
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred.",
            }
        }
        return JSONResponse(error_response, status_code=500)


async def health_check(_: Request) -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({"status": "ok"})


def setup_rest_routes() -> list[Route]:
    """Create REST API v1 routes."""
    routes = [
        Route("/v1/tools", endpoint=list_tools_endpoint, methods=["GET"]),
        Route(
            "/v1/tools/{tool_name}/invoke",
            endpoint=tool_invocation_endpoint,
            methods=["POST"],
        ),
    ]
    return routes
