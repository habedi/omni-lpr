import asyncio
import base64
import io
import json
import logging
from dataclasses import asdict
from functools import partial
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Callable,
    Coroutine,
    Literal,
    Optional,
    Type,
    get_args,
)

import anyio
import httpx
import mcp.types as types
import numpy as np
from PIL import Image, UnidentifiedImageError
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError

from .errors import ErrorCode, ToolLogicError
from .settings import settings

if TYPE_CHECKING:
    from fast_alpr import ALPR
    from fast_plate_ocr import LicensePlateRecognizer

_logger = logging.getLogger(__name__)
_ocr_model_cache: dict[str, "LicensePlateRecognizer"] = {}
_alpr_cache: dict[tuple[str, str], "ALPR"] = {}
_ocr_lock = asyncio.Lock()
_alpr_lock = asyncio.Lock()


# --- Reusable Pydantic Types and Validators ---
def _validate_base64(v: Any, _: ValidationInfo) -> str:
    """Validator to ensure a string is valid Base64."""
    if not isinstance(v, str):
        raise PydanticCustomError("not_base64_string", "A valid Base64 string is required.")
    if not v:
        raise ValueError("image_base64 cannot be empty.")
    if len(v) > 7000000:
        raise ValueError("Input image is too large. The maximum size is 5MB.")
    try:
        base64.b64decode(v)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid base64 string provided. Error: {e}") from e
    return v


from pydantic import BeforeValidator

# Annotated type for Base64 image strings
Base64ImageStr = Annotated[str, BeforeValidator(_validate_base64)]


# --- Define allowed models as Literal types for validation ---
DetectorModel = Literal[
    "yolo-v9-s-608-license-plate-end2end",
    "yolo-v9-t-640-license-plate-end2end",
    "yolo-v9-t-512-license-plate-end2end",
    "yolo-v9-t-416-license-plate-end2end",
    "yolo-v9-t-384-license-plate-end2end",
    "yolo-v9-t-256-license-plate-end2end",
]

OcrModel = Literal["cct-s-v1-global-model", "cct-xs-v1-global-model"]


# --- Pydantic Models for Input Validation ---
# These will be defined inside the setup_tools function after settings are loaded.
# This allows us to use the loaded settings for default values in the schema.
class RecognizePlateArgs(BaseModel):
    pass


class DetectAndRecognizePlateArgs(BaseModel):
    pass


class ListModelsArgs(BaseModel):
    """Input arguments for listing available models."""

    model_config = ConfigDict(extra="forbid")


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, callable] = {}
        self._tool_definitions: list[types.Tool] = []
        self._tool_models: dict[str, Type[BaseModel]] = {}

    def register(self, tool_definition: types.Tool, model: Type[BaseModel]):
        def decorator(func: callable) -> callable:
            name = tool_definition.name
            if name in self._tools:
                raise ValueError(f"Tool '{name}' is already registered.")
            self._tools[name] = func
            self._tool_definitions.append(tool_definition)
            self._tool_models[name] = model
            return func

        return decorator

    def register_tool(self, tool_definition: types.Tool, model: Type[BaseModel], func: callable):
        """Register a tool directly without using a decorator."""
        name = tool_definition.name
        if name in self._tools:
            raise ValueError(f"Tool '{name}' is already registered.")
        self._tools[name] = func
        self._tool_definitions.append(tool_definition)
        self._tool_models[name] = model

    async def call_validated(
        self, name: str, validated_args: BaseModel
    ) -> list[types.ContentBlock]:
        """Executes the tool with already validated arguments."""
        func = self._tools[name]
        try:
            return await func(validated_args)
        except ToolLogicError:
            raise  # Don't re-wrap our own errors
        except Exception as e:
            error_message = f"An unexpected error occurred in tool '{name}': {e}"
            _logger.exception(error_message)
            raise ToolLogicError(
                message=error_message,
                code=ErrorCode.TOOL_LOGIC_ERROR,
            ) from e

    async def call(self, name: str, arguments: dict) -> list[types.ContentBlock]:
        if name not in self._tools:
            _logger.warning(f"Unknown tool requested: {name}")
            raise ToolLogicError(message=f"Unknown tool: {name}", code=ErrorCode.VALIDATION_ERROR)

        model = self._tool_models.get(name)
        if not model:
            raise ToolLogicError(
                message=f"No validation model registered for tool '{name}'.",
                code=ErrorCode.UNKNOWN_ERROR,
            )

        try:
            validated_args = model(**arguments)
        except ValidationError as e:
            _logger.error(f"Input validation failed for tool '{name}': {e}")
            raise ToolLogicError(
                message=f"Input validation failed for tool '{name}'.",
                code=ErrorCode.VALIDATION_ERROR,
                details=e.errors(),
            ) from e

        return await self.call_validated(name, validated_args)

    def list(self) -> list[types.Tool]:
        return self._tool_definitions


tool_registry = ToolRegistry()


async def _get_ocr_recognizer(ocr_model: str) -> "LicensePlateRecognizer":
    async with _ocr_lock:
        if ocr_model not in _ocr_model_cache:
            _logger.info(f"Loading license plate OCR model: {ocr_model}")
            from fast_plate_ocr import LicensePlateRecognizer

            recognizer = await anyio.to_thread.run_sync(LicensePlateRecognizer, ocr_model)
            _ocr_model_cache[ocr_model] = recognizer
    return _ocr_model_cache[ocr_model]


async def _get_image_from_source(
    *, image_base64: Optional[str] = None, path: Optional[str] = None
) -> Image.Image:
    """
    Retrieves an image from either a Base64 string or a path/URL.

    Returns a PIL Image object in RGB format.
    """
    image_bytes: Optional[bytes] = None
    source_for_error_msg = ""

    if image_base64:
        source_for_error_msg = "Base64 data"
        image_bytes = base64.b64decode(image_base64)

    elif path:
        source_for_error_msg = f"path '{path}'"
        if path.startswith(("http://", "https://")):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(path)
                    response.raise_for_status()
                    image_bytes = await response.aread()
            except httpx.HTTPStatusError as e:
                raise ValueError(f"Failed to fetch image from URL: {e.response.status_code}") from e
        else:
            try:
                image_bytes = await anyio.Path(path).read_bytes()
            except FileNotFoundError:
                raise ValueError(f"File not found at path: {path}")

    if not image_bytes:
        # This should not be reached if the Pydantic model validation is correct
        raise ValueError("No image source provided.")

    try:
        image = Image.open(io.BytesIO(image_bytes))
        return image.convert("RGB")
    except UnidentifiedImageError as e:
        raise ValueError(f"Data from {source_for_error_msg} is not a valid image file.") from e


async def recognize_plate(args: RecognizePlateArgs) -> list[types.ContentBlock]:
    image_rgb = await _get_image_from_source(
        image_base64=getattr(args, "image_base64", None), path=getattr(args, "path", None)
    )
    recognizer = await _get_ocr_recognizer(args.ocr_model)  # type: ignore
    image_np = np.array(image_rgb)
    result = await anyio.to_thread.run_sync(recognizer.run, image_np)

    _logger.info(f"License plate recognized: {result}")
    return [types.TextContent(type="text", text=json.dumps(result))]


async def _get_alpr_instance(detector_model: str, ocr_model: str) -> "ALPR":
    cache_key = (detector_model, ocr_model)
    async with _alpr_lock:
        if cache_key not in _alpr_cache:
            _logger.info(
                f"Loading ALPR instance with detector '{detector_model}' and OCR '{ocr_model}'"
            )
            from fast_alpr import ALPR

            alpr_constructor = partial(ALPR, detector_model=detector_model, ocr_model=ocr_model)
            alpr_instance = await anyio.to_thread.run_sync(alpr_constructor)
            _alpr_cache[cache_key] = alpr_instance
    return _alpr_cache[cache_key]


async def detect_and_recognize_plate(args: DetectAndRecognizePlateArgs) -> list[types.ContentBlock]:
    image_rgb = await _get_image_from_source(
        image_base64=getattr(args, "image_base64", None), path=getattr(args, "path", None)
    )
    alpr = await _get_alpr_instance(args.detector_model, args.ocr_model)  # type: ignore
    image_np = np.array(image_rgb)
    results = await anyio.to_thread.run_sync(alpr.predict, image_np)

    results_dict = [asdict(res) for res in results]

    _logger.info(f"ALPR processed. Found {len(results_dict)} plate(s).")
    return [types.TextContent(type="text", text=json.dumps(results_dict))]


async def list_models(_: ListModelsArgs) -> list[types.ContentBlock]:
    """Lists available detector and OCR models."""
    models = {
        "detector_models": list(get_args(DetectorModel)),
        "ocr_models": list(get_args(OcrModel)),
    }
    return [types.TextContent(type="text", text=json.dumps(models))]


def setup_tools():
    """
    Defines and registers all tools in the tool registry.

    This function is called after the main application settings are loaded,
    allowing us to define Pydantic models with defaults based on those settings.
    This ensures that the generated JSON schemas for the tools are accurate
    without needing manual patching.
    """
    # --- Dynamically Defined Pydantic Models ---

    class _BaseImageToolArgs(BaseModel):
        model_config = ConfigDict(extra="forbid")
        image_base64: Optional[Base64ImageStr] = None
        path: Optional[str] = None

        @model_validator(mode="after")
        def check_one_of_image_or_path(self) -> "Self":
            if self.image_base64 is None and self.path is None:
                raise ValueError("Exactly one of 'image_base64' or 'path' must be provided.")
            if self.image_base64 is not None and self.path is not None:
                raise ValueError("Exactly one of 'image_base64' or 'path' must be provided.")
            return self

        @field_validator("path")
        @classmethod
        def path_must_not_be_empty(cls, v: str) -> str:
            if not v or not v.strip():
                raise ValueError("Path cannot be empty.")
            return v

    # The actual models used by the tool functions are defined here.
    # We redefine the global names so that other parts of the code can see the updated classes.
    global RecognizePlateArgs, DetectAndRecognizePlateArgs

    class RecognizePlateArgs(_BaseImageToolArgs):  # type: ignore
        """Input arguments for recognizing a license plate."""

        ocr_model: OcrModel = Field(default=settings.default_ocr_model)

    class DetectAndRecognizePlateArgs(_BaseImageToolArgs):  # type: ignore
        """Input arguments for detecting and recognizing a license plate."""

        detector_model: DetectorModel = "yolo-v9-t-384-license-plate-end2end"
        ocr_model: OcrModel = Field(default=settings.default_ocr_model)

    # --- Tool Registration ---

    # Tool: recognize_plate
    recognize_plate_tool_definition = types.Tool(
        name="recognize_plate",
        title="License Plate Recognizer",
        description="Recognizes text from an image of a license plate, provided as a Base64 string or a local/URL path.",
        inputSchema=RecognizePlateArgs.model_json_schema(),
    )
    tool_registry.register_tool(
        tool_definition=recognize_plate_tool_definition,
        model=RecognizePlateArgs,
        func=recognize_plate,
    )

    # Tool: detect_and_recognize_plate
    detect_and_recognize_plate_tool_definition = types.Tool(
        name="detect_and_recognize_plate",
        title="Detect and Recognize License Plate",
        description="Detects license plates in an image and recognizes the text, from a Base64 string or a local/URL path.",
        inputSchema=DetectAndRecognizePlateArgs.model_json_schema(),
    )
    tool_registry.register_tool(
        tool_definition=detect_and_recognize_plate_tool_definition,
        model=DetectAndRecognizePlateArgs,
        func=detect_and_recognize_plate,
    )

    # Tool: list_models
    list_models_tool_definition = types.Tool(
        name="list_models",
        title="List Available Models",
        description="Lists the available detector and OCR models for the full ALPR process.",
        inputSchema=ListModelsArgs.model_json_schema(),
    )
    tool_registry.register_tool(
        tool_definition=list_models_tool_definition,
        model=ListModelsArgs,
        func=list_models,
    )
