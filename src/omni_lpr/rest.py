# src/omni_lpr/rest.py
import base64
import json
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
from .settings import settings
from .tools import tool_registry

# Initialize logger
_logger = logging.getLogger(__name__)

# 1. Initialize Spectree for API documentation generation
# This instance will be used to decorate and document our endpoints.
api_spec = SpecTree(
    "starlette",
    title="Omni-LPR REST API",
    description="A multi-interface server for automatic license plate recognition.",
    version=settings.pkg_version,
    mode="strict",
    swagger_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
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


async def _parse_tool_arguments(request: Request, model: BaseModel) -> BaseModel:
    """
    Parses tool arguments from the request based on Content-Type.
    Handles 'application/json' and 'multipart/form-data'.
    """
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        _logger.debug("Processing 'application/json' request.")
        body = await request.body()
        json_data = json.loads(body) if body else {}
        return model(**json_data)

    if "multipart/form-data" in content_type:
        _logger.debug("Processing 'multipart/form-data' request.")
        form = await request.form()
        image_upload = form.get("image")
        if not image_upload:
            raise ValueError("Missing 'image' part in multipart form.")

        image_bytes = await image_upload.read()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        params = {k: v for k, v in form.items() if k != "image"}
        params["image_base64"] = image_base64
        return model(**params)

    # Handle cases with no body or unsupported content types
    if model.model_fields:
        _logger.warning(f"Unsupported Content-Type: {content_type}")
        raise ValueError("Unsupported Content-Type. Use application/json or multipart/form-data.")
    else:
        return model()


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

    if tool_name not in tool_registry._tools:
        error = ErrorResponse(
            error={"code": "NOT_FOUND", "message": f"Tool '{tool_name}' not found."}
        )
        return JSONResponse(error.model_dump(), status_code=404)

    input_model = tool_registry._tool_models.get(tool_name, BaseModel)

    try:
        validated_args = await _parse_tool_arguments(request, input_model)
        mcp_content_blocks = await tool_registry.call_validated(tool_name, validated_args)
        api_content_blocks = [
            JsonContentBlock(data=json.loads(block.text)) for block in mcp_content_blocks
        ]
        response_data = ToolResponse(content=api_content_blocks)
        return JSONResponse(response_data.model_dump())

    except ValidationError as e:
        error = ErrorResponse(
            error={
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed.",
                "details": e.errors(),
            }
        )
        return JSONResponse(error.model_dump(), status_code=400)
    except (json.JSONDecodeError, ValueError) as e:
        error = ErrorResponse(error={"code": "BAD_REQUEST", "message": str(e)})
        return JSONResponse(error.model_dump(), status_code=400)
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
