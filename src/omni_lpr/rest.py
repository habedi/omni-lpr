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

# Initialize Spectree for API documentation generation
api_spec = SpecTree(
    "starlette",
    title="Omni-LPR REST API",
    description="A multi-interface server for automatic license plate recognition.",
    version=settings.pkg_version,
    mode="strict",
    # Fix: Make doc paths relative to the sub-app's root
    swagger_url="/docs",
    redoc_url="/redoc",
    naming_strategy=lambda model: model.__name__,
)


@api_spec.validate(resp=Response(HTTP_200=ToolListResponse), tags=["Tool Listing"])
async def list_tools(request: Request) -> JSONResponse:
    """
    Lists all available tools.
    """
    tools = tool_registry.list()
    tool_dicts = [dict(t) for t in tools]
    response_data = ToolListResponse(tools=tool_dicts)
    return JSONResponse(response_data.model_dump())


async def _parse_tool_arguments(request: Request, model: BaseModel) -> BaseModel:
    """
    Parses and validates tool arguments from an incoming request.
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

    if model.model_fields:
        _logger.warning(f"Unsupported Content-Type: {content_type}")
        raise ValueError("Unsupported Content-Type. Use application/json or multipart/form-data.")
    else:
        return model()


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


def setup_rest_routes() -> list[Route]:
    """
    Creates and decorates all REST API routes.
    """
    routes = [
        Route("/tools", endpoint=list_tools, methods=["GET"]),
        Route("/tools/{tool_name}/invoke", endpoint=invoke_tool, methods=["POST"]),
    ]
    return routes
