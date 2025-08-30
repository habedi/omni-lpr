import asyncio
import base64
import io
import json
import logging
from dataclasses import asdict
from functools import partial
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Literal, Type, get_args

import anyio
import httpx
import mcp.types as types
import numpy as np
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

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
class RecognizePlateArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_base64: str
    ocr_model: OcrModel = Field(default_factory=lambda: settings.default_ocr_model)

    @field_validator("image_base64")
    @classmethod
    def validate_image_base64(cls, v: str) -> str:
        if not v:
            raise ValueError("image_base64 cannot be empty.")
        if len(v) > 7000000:
            raise ValueError("Input image is too large. The maximum size is 5MB.")
        try:
            base64.b64decode(v)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid base64 string provided. Error: {e}") from e
        return v


class RecognizePlateFromPathArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    ocr_model: OcrModel = Field(default_factory=lambda: settings.default_ocr_model)

    @field_validator("path")
    @classmethod
    def path_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Path cannot be empty.")
        return v


class DetectAndRecognizePlateArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_base64: str
    detector_model: DetectorModel = "yolo-v9-t-384-license-plate-end2end"
    ocr_model: OcrModel = Field(default_factory=lambda: settings.default_ocr_model)

    @field_validator("image_base64")
    @classmethod
    def validate_image_base64(cls, v: str) -> str:
        if not v:
            raise ValueError("image_base64 cannot be empty.")
        if len(v) > 7000000:
            raise ValueError("Input image is too large. The maximum size is 5MB.")
        try:
            base64.b64decode(v)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid base64 string provided. Error: {e}") from e
        return v


class DetectAndRecognizePlateFromPathArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    detector_model: DetectorModel = "yolo-v9-t-384-license-plate-end2end"
    ocr_model: OcrModel = Field(default_factory=lambda: settings.default_ocr_model)

    @field_validator("path")
    @classmethod
    def path_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Path cannot be empty.")
        return v


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


async def _get_image_from_base64(encoded_str: str) -> Image.Image:
    """Decodes a base64 string and returns a PIL Image."""
    try:
        image_bytes = base64.b64decode(encoded_str)
        image = Image.open(io.BytesIO(image_bytes))
        return image.convert("RGB")
    except UnidentifiedImageError as e:
        raise ValueError("Invalid image data provided. Could not decode image.") from e


async def _run_on_path(path: str, model_runner: Callable[[Any], Coroutine[Any, Any, Any]]):
    """
    Runs a model on an image from a path, handling URL downloading.
    """
    try:
        if path.startswith(("http://", "https://")):
            async with httpx.AsyncClient() as client:
                response = await client.get(path)
                response.raise_for_status()
                image_bytes = await response.aread()
            image = Image.open(io.BytesIO(image_bytes))
            image_rgb = image.convert("RGB")
            image_np = np.array(image_rgb)
            return await anyio.to_thread.run_sync(model_runner, image_np)
        else:
            return await anyio.to_thread.run_sync(model_runner, path)
    except FileNotFoundError:
        raise ValueError(f"File not found at path: {path}")
    except httpx.HTTPStatusError as e:
        raise ValueError(f"Failed to fetch image from URL: {e.response.status_code}")
    except UnidentifiedImageError:
        raise ValueError(f"Data from path '{path}' is not a valid image file.")


async def recognize_plate(args: RecognizePlateArgs) -> list[types.ContentBlock]:
    image_rgb = await _get_image_from_base64(args.image_base64)
    recognizer = await _get_ocr_recognizer(args.ocr_model)
    image_np = np.array(image_rgb)
    result = await anyio.to_thread.run_sync(recognizer.run, image_np)

    _logger.info(f"License plate recognized: {result}")
    return [types.TextContent(type="text", text=json.dumps(result))]


async def recognize_plate_from_path(args: RecognizePlateFromPathArgs) -> list[types.ContentBlock]:
    path = args.path
    recognizer = await _get_ocr_recognizer(args.ocr_model)
    result = await _run_on_path(path, recognizer.run)

    _logger.info(f"License plate recognized from source '{path}': {result}")
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
    image_rgb = await _get_image_from_base64(args.image_base64)
    alpr = await _get_alpr_instance(args.detector_model, args.ocr_model)
    image_np = np.array(image_rgb)
    results = await anyio.to_thread.run_sync(alpr.predict, image_np)

    results_dict = [asdict(res) for res in results]

    _logger.info(f"ALPR processed. Found {len(results_dict)} plate(s).")
    return [types.TextContent(type="text", text=json.dumps(results_dict))]


async def detect_and_recognize_plate_from_path(
    args: DetectAndRecognizePlateFromPathArgs,
) -> list[types.ContentBlock]:
    path = args.path
    alpr = await _get_alpr_instance(args.detector_model, args.ocr_model)
    results = await _run_on_path(path, alpr.predict)

    results_dict = [asdict(res) for res in results]
    _logger.info(f"ALPR processed source '{path}'. Found {len(results_dict)} plate(s).")
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

    This function is called after the main application settings are loaded
    to ensure that tool schemas are generated with the correct default values.
    """
    # --- Tool Definitions and Implementations ---
    # For each tool, we generate the schema and then manually inject the dynamic
    # default value for the ocr_model, as Pydantic's `default_factory` does not
    # include the default value in the generated JSON schema.

    # Tool: recognize_plate
    recognize_plate_schema = RecognizePlateArgs.model_json_schema()
    recognize_plate_schema["properties"]["ocr_model"]["default"] = settings.default_ocr_model
    recognize_plate_tool_definition = types.Tool(
        name="recognize_plate",
        title="License Plate Recognizer",
        description="Recognizes text from a cropped image of a license plate.",
        inputSchema=recognize_plate_schema,
    )
    tool_registry.register_tool(
        tool_definition=recognize_plate_tool_definition,
        model=RecognizePlateArgs,
        func=recognize_plate,
    )

    # Tool: recognize_plate_from_path
    recognize_plate_from_path_schema = RecognizePlateFromPathArgs.model_json_schema()
    recognize_plate_from_path_schema["properties"]["ocr_model"]["default"] = (
        settings.default_ocr_model
    )
    recognize_plate_from_path_tool_definition = types.Tool(
        name="recognize_plate_from_path",
        title="License Plate Recognizer from Path",
        description="Recognizes text from a cropped image located at a given URL or local file path.",
        inputSchema=recognize_plate_from_path_schema,
    )
    tool_registry.register_tool(
        tool_definition=recognize_plate_from_path_tool_definition,
        model=RecognizePlateFromPathArgs,
        func=recognize_plate_from_path,
    )

    # Tool: detect_and_recognize_plate
    detect_and_recognize_plate_schema = DetectAndRecognizePlateArgs.model_json_schema()
    detect_and_recognize_plate_schema["properties"]["ocr_model"]["default"] = (
        settings.default_ocr_model
    )
    detect_and_recognize_plate_tool_definition = types.Tool(
        name="detect_and_recognize_plate",
        title="Detect and Recognize License Plate",
        description="Detects one or more license plates in an image and recognizes the text on each plate.",
        inputSchema=detect_and_recognize_plate_schema,
    )
    tool_registry.register_tool(
        tool_definition=detect_and_recognize_plate_tool_definition,
        model=DetectAndRecognizePlateArgs,
        func=detect_and_recognize_plate,
    )

    # Tool: detect_and_recognize_plate_from_path
    detect_and_recognize_plate_from_path_schema = (
        DetectAndRecognizePlateFromPathArgs.model_json_schema()
    )
    detect_and_recognize_plate_from_path_schema["properties"]["ocr_model"]["default"] = (
        settings.default_ocr_model
    )
    detect_and_recognize_plate_from_path_tool_definition = types.Tool(
        name="detect_and_recognize_plate_from_path",
        title="Detect and Recognize License Plate from Path",
        description="Detects and recognizes license plates from an image at a given URL or local file path.",
        inputSchema=detect_and_recognize_plate_from_path_schema,
    )
    tool_registry.register_tool(
        tool_definition=detect_and_recognize_plate_from_path_tool_definition,
        model=DetectAndRecognizePlateFromPathArgs,
        func=detect_and_recognize_plate_from_path,
    )

    # Tool: list_models (no default OCR model)
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
