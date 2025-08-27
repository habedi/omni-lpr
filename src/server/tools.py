import base64
import io
import json
import logging
from dataclasses import asdict
from functools import partial
from typing import TYPE_CHECKING, Literal, Type

import anyio
import httpx
import mcp.types as types
import numpy as np
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field, ValidationError, field_validator

from .errors import ErrorCode, ToolLogicError
from .settings import settings

if TYPE_CHECKING:
    from fast_alpr import ALPR
    from fast_plate_ocr import LicensePlateRecognizer

_logger = logging.getLogger(__name__)
_ocr_model_cache: dict[str, "LicensePlateRecognizer"] = {}
_alpr_cache: dict[tuple[str, str], "ALPR"] = {}


# --- Pydantic Models for Input Validation ---
class RecognizePlateArgs(BaseModel):
    image_base64: str
    model_name: Literal["cct-s-v1-global-model", "cct-xs-v1-global-model"] = Field(
        default_factory=lambda: settings.default_ocr_model
    )

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
    path: str
    model_name: Literal["cct-s-v1-global-model", "cct-xs-v1-global-model"] = Field(
        default_factory=lambda: settings.default_ocr_model
    )

    @field_validator("path")
    @classmethod
    def path_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Path cannot be empty.")
        return v


class DetectAndRecognizePlateArgs(BaseModel):
    image_base64: str
    detector_model: str = "yolo-v9-t-384-license-plate-end2end"
    ocr_model: str = Field(default_factory=lambda: settings.default_ocr_model)

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
    path: str
    detector_model: str = "yolo-v9-t-384-license-plate-end2end"
    ocr_model: str = Field(default_factory=lambda: settings.default_ocr_model)

    @field_validator("path")
    @classmethod
    def path_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Path cannot be empty.")
        return v


class ListModelsArgs(BaseModel):
    """Input arguments for listing available models."""

    pass


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

# --- Tool Definitions and Implementations ---
recognize_plate_tool_definition = types.Tool(
    name="recognize_plate",
    title="License Plate Recognizer",
    description="Recognizes text from a cropped image of a license plate.",
    inputSchema=RecognizePlateArgs.model_json_schema(),
)


async def _get_ocr_recognizer(model_name: str) -> "LicensePlateRecognizer":
    if model_name not in _ocr_model_cache:
        _logger.info(f"Loading license plate OCR model: {model_name}")
        from fast_plate_ocr import LicensePlateRecognizer

        recognizer = await anyio.to_thread.run_sync(LicensePlateRecognizer, model_name)
        _ocr_model_cache[model_name] = recognizer
    return _ocr_model_cache[model_name]


@tool_registry.register(recognize_plate_tool_definition, RecognizePlateArgs)
async def recognize_plate(args: RecognizePlateArgs) -> list[types.ContentBlock]:
    try:
        image_bytes = base64.b64decode(args.image_base64)
        image = Image.open(io.BytesIO(image_bytes))
        image_rgb = image.convert("RGB")
    except UnidentifiedImageError as e:
        raise ValueError(f"Invalid image data provided. Could not decode image. Error: {e}") from e

    recognizer = await _get_ocr_recognizer(args.model_name)
    image_np = np.array(image_rgb)
    result = await anyio.to_thread.run_sync(recognizer.run, image_np)

    _logger.info(f"License plate recognized: {result}")
    return [types.TextContent(type="text", text=json.dumps(result))]


recognize_plate_from_path_tool_definition = types.Tool(
    name="recognize_plate_from_path",
    title="License Plate Recognizer from Path",
    description="Recognizes text from a cropped image located at a given URL or local file path.",
    inputSchema=RecognizePlateFromPathArgs.model_json_schema(),
)


@tool_registry.register(recognize_plate_from_path_tool_definition, RecognizePlateFromPathArgs)
async def recognize_plate_from_path(args: RecognizePlateFromPathArgs) -> list[types.ContentBlock]:
    path = args.path
    try:
        recognizer = await _get_ocr_recognizer(args.model_name)
        if path.startswith("http://") or path.startswith("https://"):
            async with httpx.AsyncClient() as client:
                response = await client.get(path)
                response.raise_for_status()
                image_bytes = await response.aread()
            image = Image.open(io.BytesIO(image_bytes))
            image_rgb = image.convert("RGB")
            image_np = np.array(image_rgb)
            result = await anyio.to_thread.run_sync(recognizer.run, image_np)
        else:
            result = await anyio.to_thread.run_sync(recognizer.run, path)

    except FileNotFoundError:
        raise ValueError(f"File not found at path: {path}")
    except httpx.HTTPStatusError as e:
        raise ValueError(
            f"Failed to fetch image from URL: {e.response.status_code} {e.response.reason_phrase}"
        )
    except UnidentifiedImageError as e:
        raise ValueError(f"Data from path '{path}' is not a valid image file. Error: {e}") from e
    except Exception as e:
        raise ValueError(f"Could not process image from path '{path}': {e}")

    _logger.info(f"License plate recognized from source '{path}': {result}")
    return [types.TextContent(type="text", text=json.dumps(result))]


async def _get_alpr_instance(detector_model: str, ocr_model: str) -> "ALPR":
    cache_key = (detector_model, ocr_model)
    if cache_key not in _alpr_cache:
        _logger.info(
            f"Loading ALPR instance with detector '{detector_model}' and OCR '{ocr_model}'"
        )
        from fast_alpr import ALPR

        alpr_constructor = partial(ALPR, detector_model=detector_model, ocr_model=ocr_model)
        alpr_instance = await anyio.to_thread.run_sync(alpr_constructor)
        _alpr_cache[cache_key] = alpr_instance
    return _alpr_cache[cache_key]


detect_and_recognize_plate_tool_definition = types.Tool(
    name="detect_and_recognize_plate",
    title="Detect and Recognize License Plate",
    description="Detects one or more license plates in an image and recognizes the text on each plate.",
    inputSchema=DetectAndRecognizePlateArgs.model_json_schema(),
)


@tool_registry.register(detect_and_recognize_plate_tool_definition, DetectAndRecognizePlateArgs)
async def detect_and_recognize_plate(args: DetectAndRecognizePlateArgs) -> list[types.ContentBlock]:
    try:
        image_bytes = base64.b64decode(args.image_base64)
        image = Image.open(io.BytesIO(image_bytes))
        image_rgb = image.convert("RGB")
    except UnidentifiedImageError as e:
        raise ValueError(f"Invalid image data. Could not decode image. Error: {e}") from e

    alpr = await _get_alpr_instance(args.detector_model, args.ocr_model)
    image_np = np.array(image_rgb)
    results = await anyio.to_thread.run_sync(alpr.predict, image_np)

    results_dict = [asdict(res) for res in results]

    _logger.info(f"ALPR processed. Found {len(results_dict)} plate(s).")
    return [types.TextContent(type="text", text=json.dumps(results_dict))]


detect_and_recognize_plate_from_path_tool_definition = types.Tool(
    name="detect_and_recognize_plate_from_path",
    title="Detect and Recognize License Plate from Path",
    description="Detects and recognizes license plates from an image at a given URL or local file path.",
    inputSchema=DetectAndRecognizePlateFromPathArgs.model_json_schema(),
)


@tool_registry.register(
    detect_and_recognize_plate_from_path_tool_definition, DetectAndRecognizePlateFromPathArgs
)
async def detect_and_recognize_plate_from_path(
    args: DetectAndRecognizePlateFromPathArgs,
) -> list[types.ContentBlock]:
    path = args.path
    try:
        alpr = await _get_alpr_instance(args.detector_model, args.ocr_model)
        if path.startswith("http://") or path.startswith("https://"):
            async with httpx.AsyncClient() as client:
                response = await client.get(path)
                response.raise_for_status()
                image_bytes = await response.aread()
            image = Image.open(io.BytesIO(image_bytes))
            image_rgb = image.convert("RGB")
            image_np = np.array(image_rgb)
            results = await anyio.to_thread.run_sync(alpr.predict, image_np)
        else:
            results = await anyio.to_thread.run_sync(alpr.predict, path)

    except FileNotFoundError:
        raise ValueError(f"File not found at path: {path}")
    except httpx.HTTPStatusError as e:
        raise ValueError(
            f"Failed to fetch image from URL: {e.response.status_code} {e.response.reason_phrase}"
        )
    except UnidentifiedImageError as e:
        raise ValueError(f"Data from path '{path}' is not a valid image file. Error: {e}") from e
    except Exception as e:
        raise ValueError(f"Could not process image from path '{path}': {e}")

    results_dict = [asdict(res) for res in results]
    _logger.info(f"ALPR processed source '{path}'. Found {len(results_dict)} plate(s).")
    return [types.TextContent(type="text", text=json.dumps(results_dict))]


list_models_tool_definition = types.Tool(
    name="list_models",
    title="List Available Models",
    description="Lists the available detector and OCR models for the full ALPR process.",
    inputSchema=ListModelsArgs.model_json_schema(),
)


@tool_registry.register(list_models_tool_definition, ListModelsArgs)
async def list_models(_: ListModelsArgs) -> list[types.ContentBlock]:
    """Lists available detector and OCR models."""
    models = {
        "detector_models": [
            "yolo-v9-t-384-license-plate-end2end",
        ],
        "ocr_models": ["cct-s-v1-global-model", "cct-xs-v1-global-model"],
    }
    return [types.TextContent(type="text", text=json.dumps(models))]
