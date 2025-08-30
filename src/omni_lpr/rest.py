import json
import logging
from typing import Type

from mcp import types
from pydantic import BaseModel, ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from .errors import APIError, ErrorCode
from .tools import tool_registry

_logger = logging.getLogger(__name__)


def create_rest_endpoint(tool_name: str, tool_func: callable, model: Type[BaseModel]) -> Route:
    """Create a Starlette REST endpoint for a given tool."""

    async def endpoint(request: Request) -> JSONResponse:
        _logger.info(f"REST endpoint '{tool_name}' called.")
        try:
            if await request.body():
                json_data = await request.json()
            else:
                json_data = {}

        except json.JSONDecodeError:
            _logger.warning(f"Invalid JSON received for tool '{tool_name}'.")
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        try:
            validated_args = model(**json_data)
        except ValidationError as e:
            _logger.warning(f"Input validation failed for tool '{tool_name}': {e}")
            return JSONResponse(
                {"error": "Input validation failed", "details": e.errors()},
                status_code=400,
            )

        try:
            result_content: list[types.ContentBlock] = await tool_func(validated_args)
            # The result from the tool is a list of ContentBlock objects.
            # We need to serialize them to a JSON-compatible format.
            results = []
            for item in result_content:
                if isinstance(item, types.TextContent):
                    if not item.text:
                        continue  # Skip empty text content
                    try:
                        results.append(json.loads(item.text))
                    except json.JSONDecodeError as e:
                        _logger.warning(
                            f"Failed to decode JSON from tool output for '{tool_name}': {e}"
                        )
                        error = APIError(
                            code=ErrorCode.DESERIALIZATION_ERROR,
                            message="A tool returned output that could not be decoded as JSON.",
                            details={"raw_output": item.text},
                        )
                        return JSONResponse({"errors": [error.model_dump()]}, status_code=500)
                else:
                    results.append(item.model_dump())

            if not results:
                return JSONResponse({})

            # If the original tool result was a single item that we parsed into a list,
            # unwrap it for a cleaner API response.
            final_result = (
                results[0] if len(results) == 1 and isinstance(results[0], list) else results
            )
            final_result = final_result[0] if len(final_result) == 1 else final_result
            return JSONResponse(final_result)

        except ValueError as e:
            _logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
            return JSONResponse({"error": str(e)}, status_code=400)
        except Exception as e:
            _logger.error(f"An unexpected error occurred in tool '{tool_name}': {e}", exc_info=True)
            return JSONResponse({"error": "An internal server error occurred"}, status_code=500)

    return Route(f"/{tool_name}", endpoint=endpoint, methods=["POST"])


def setup_rest_routes() -> list[Route]:
    """Create REST API routes for all registered tools."""
    routes = []
    for tool_name, tool_impl in tool_registry._tools.items():
        model = tool_registry._tool_models[tool_name]
        route = create_rest_endpoint(tool_name, tool_impl, model)
        routes.append(route)

    async def list_tools_endpoint(_request) -> JSONResponse:
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
        return JSONResponse(tools_info)

    routes.append(Route("/tools", endpoint=list_tools_endpoint, methods=["GET"]))
    return routes
