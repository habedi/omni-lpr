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
from async_lru import alru_cache
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
)
from pydantic_core import PydanticCustomError

from .errors import ErrorCode, ToolLogicError
from .settings import settings

if TYPE_CHECKING:
    from fast_alpr import ALPR
    from fast_plate_ocr import LicensePlateRecognizer

_logger = logging.getLogger(__name__)


# --- Reusable Pydantic Types and Validators ---
def _validate_base64(v: Any, _: ValidationInfo) -> str:
    """Validator to ensure a string is valid Base64."""
    if not isinstance(v, str):
        raise PydanticCustomError("not_base64_string", "A valid Base64 string is required.")
    if not v:
        raise ValueError("image_base64 cannot be empty.")

    # Calculate the maximum allowed Base64 string length for a given image size in MB.
    # Base64 encoding increases the size by a factor of 4/3.
    max_len = int(settings.max_image_size_mb * 1024 * 1024 * 4 / 3)
    if len(v) > max_len:
        raise ValueError(
            f"Input image is too large. The maximum size is {settings.max_image_size_mb}MB."
        )

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
# These models are placeholders. The actual models with dynamic default
# values are defined and used within the setup_tools() function.
class RecognizePlateArgs(BaseModel):
    pass


class RecognizePlateFromPathArgs(BaseModel):
    pass


class DetectAndRecognizePlateArgs(BaseModel):
    pass


class DetectAndRecognizePlateFromPathArgs(BaseModel):
    pass


class ListModelsArgs(BaseModel):
    """Input arguments for listing available models."""

    model_config = ConfigDict(extra="forbid")


class ToolRegistry:
    """
    Manages the registration and execution of tools.

    This class provides a centralized mechanism to register tools, their
    definitions, and their input validation models. It handles the dynamic
    calling of tools, including input validation and error handling.
    """

    def __init__(self):
        """Initializes the ToolRegistry with empty storage for tools."""
        self._tools: dict[str, callable] = {}
        self._tool_definitions: list[types.Tool] = []
        self._tool_models: dict[str, Type[BaseModel]] = {}

    def register(self, tool_definition: types.Tool, model: Type[BaseModel]):
        """
        Returns a decorator to register a tool with its definition and model.

        Args:
            tool_definition: The MCP tool definition.
            model: The Pydantic model for input validation.

        Returns:
            A decorator that registers the decorated function as a tool.
        """

        def decorator(func: callable) -> callable:
            """
            Decorator to register a tool function.

            Args:
                func: The async tool function to register.

            Returns:
                The original function, now registered as a tool.
            """
            self.register_tool(tool_definition, model, func)
            return func

        return decorator

    def register_tool(self, tool_definition: types.Tool, model: Type[BaseModel], func: callable):
        """
        Registers a tool directly without using a decorator.

        Args:
            tool_definition: The MCP tool definition.
            model: The Pydantic model for input validation.
            func: The async tool function to register.

        Raises:
            ValueError: If a tool with the same name is already registered.
        """
        name = tool_definition.name
        if name in self._tools:
            raise ValueError(f"Tool '{name}' is already registered.")
        self._tools[name] = func
        self._tool_definitions.append(tool_definition)
        self._tool_models[name] = model

    async def call_validated(
        self, name: str, validated_args: BaseModel
    ) -> list[types.ContentBlock]:
        """
        Executes a tool with already validated Pydantic model arguments.

        This method is an internal-facing counterpart to `call`. It bypasses
        the validation step and directly executes the tool's logic.

        Args:
            name: The name of the tool to execute.
            validated_args: An instance of the tool's Pydantic model containing
                            the validated arguments.

        Returns:
            A list of MCP ContentBlocks produced by the tool.

        Raises:
            ToolLogicError: If the tool execution fails.
        """
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
        """
        Validates arguments and executes a tool by its name.

        This is the primary method for invoking a tool. It performs the
        following steps:
        1. Checks if the tool exists.
        2. Retrieves the associated Pydantic model for the tool.
        3. Validates the incoming `arguments` dictionary against the model.
        4. If validation succeeds, it calls the tool's implementation.
        5. If validation fails, it raises a `ToolLogicError`.

        Args:
            name: The name of the tool to call.
            arguments: A dictionary of input arguments for the tool.

        Returns:
            A list of MCP ContentBlocks produced by the tool.

        Raises:
            ToolLogicError: If the tool is unknown, no validation model is
                            registered, or input validation fails.
        """
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
        """
        Lists all registered tools.

        Returns:
            A list of MCP tool definitions.
        """
        return self._tool_definitions


tool_registry = ToolRegistry()


async def _get_ocr_recognizer(ocr_model: str) -> "LicensePlateRecognizer":
    """
    Loads and caches a license plate OCR model.
    The alru_cache decorator handles caching.
    """
    _logger.info(f"Loading license plate OCR model: {ocr_model}")
    from fast_plate_ocr import LicensePlateRecognizer

    # The LicensePlateRecognizer is not async, so we run it in a thread
    return await anyio.to_thread.run_sync(LicensePlateRecognizer, ocr_model)


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


async def _recognize_plate_logic(
    ocr_model: str, image_base64: Optional[str] = None, path: Optional[str] = None
) -> list[types.ContentBlock]:
    """Core logic to recognize a license plate from an image."""
    image_rgb = await _get_image_from_source(image_base64=image_base64, path=path)
    recognizer = await _get_ocr_recognizer(ocr_model)
    image_np = np.array(image_rgb)
    result = await anyio.to_thread.run_sync(recognizer.run, image_np)

    _logger.info(f"License plate recognized: {result}")
    return [types.TextContent(type="text", text=json.dumps(result))]


async def _get_alpr_instance(detector_model: str, ocr_model: str) -> "ALPR":
    """
    Loads and caches an ALPR instance for a given detector and OCR model.
    The alru_cache decorator handles caching.
    """
    _logger.info(
        f"Loading ALPR instance with detector '{detector_model}', "
        f"OCR '{ocr_model}', and device '{settings.execution_device}'"
    )
    from fast_alpr import ALPR

    providers = None
    # ocr_device does not support 'openvino', so we map it to 'cpu' in that case.
    ocr_device_for_alpr = (
        settings.execution_device if settings.execution_device != "openvino" else "cpu"
    )

    if settings.execution_device == "cuda":
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    elif settings.execution_device == "openvino":
        providers = ["OpenVINOExecutionProvider", "CPUExecutionProvider"]
    elif settings.execution_device == "cpu":
        providers = ["CPUExecutionProvider"]

    # The ALPR constructor is not async, so we run it in a thread
    alpr_constructor = partial(
        ALPR,
        detector_model=detector_model,
        ocr_model=ocr_model,
        ocr_device=ocr_device_for_alpr,
        detector_providers=providers,
    )
    return await anyio.to_thread.run_sync(alpr_constructor)


async def _detect_and_recognize_plate_logic(
    detector_model: str,
    ocr_model: str,
    image_base64: Optional[str] = None,
    path: Optional[str] = None,
) -> list[types.ContentBlock]:
    """Core logic to detect and recognize a license plate from an image."""
    image_rgb = await _get_image_from_source(image_base64=image_base64, path=path)
    alpr = await _get_alpr_instance(detector_model, ocr_model)
    image_np = np.array(image_rgb)
    results = await anyio.to_thread.run_sync(alpr.predict, image_np)

    results_dict = [asdict(res) for res in results]

    _logger.info(f"ALPR processed. Found {len(results_dict)} plate(s).")
    return [types.TextContent(type="text", text=json.dumps(results_dict))]


# --- Tool-specific wrapper functions ---


async def recognize_plate_base64_tool(args: "RecognizePlateArgs") -> list[types.ContentBlock]:
    """Tool wrapper for recognizing a plate from a Base64 image."""
    return await _recognize_plate_logic(ocr_model=args.ocr_model, image_base64=args.image_base64)


async def recognize_plate_path_tool(
    args: "RecognizePlateFromPathArgs",
) -> list[types.ContentBlock]:
    """Tool wrapper for recognizing a plate from an image path or URL."""
    return await _recognize_plate_logic(ocr_model=args.ocr_model, path=args.path)


async def detect_and_recognize_plate_base64_tool(
    args: "DetectAndRecognizePlateArgs",
) -> list[types.ContentBlock]:
    """Tool wrapper for detecting and recognizing a plate from a Base64 image."""
    return await _detect_and_recognize_plate_logic(
        detector_model=args.detector_model,
        ocr_model=args.ocr_model,
        image_base64=args.image_base64,
    )


async def detect_and_recognize_plate_path_tool(
    args: "DetectAndRecognizePlateFromPathArgs",
) -> list[types.ContentBlock]:
    """Tool wrapper for detecting and recognizing a plate from an image path or URL."""
    return await _detect_and_recognize_plate_logic(
        detector_model=args.detector_model, ocr_model=args.ocr_model, path=args.path
    )


async def list_models(_: ListModelsArgs) -> list[types.ContentBlock]:
    """Lists available detector and OCR models."""
    models = {
        "detector_models": list(get_args(DetectorModel)),
        "ocr_models": list(get_args(OcrModel)),
    }
    return [types.TextContent(type="text", text=json.dumps(models))]


def setup_cache():
    """
    Sets up the cache for model loading functions.

    This function must be called after the settings are finalized (e.g., after
    CLI overrides are applied) but before any tool is called. It re-wraps the
    model loading functions with an `alru_cache` decorator configured with the
    `model_cache_size` from the settings.
    """
    global _get_ocr_recognizer, _get_alpr_instance
    _get_ocr_recognizer = alru_cache(maxsize=settings.model_cache_size)(_get_ocr_recognizer)
    _get_alpr_instance = alru_cache(maxsize=settings.model_cache_size)(_get_alpr_instance)


def setup_tools():
    """
    Initializes and registers all the tools for the application.

    This function is the central point for tool setup. It defines the Pydantic
    models for each tool's arguments, using settings for default values.
    It then creates a tool definition for each tool and registers it, along with
    its corresponding model and implementation function, in the global
    `tool_registry`.

    This setup is designed to be called once at application startup.
    """

    # --- Dynamically Defined Pydantic Models ---
    # By defining these here, we can use the loaded `settings` for default values.
    global \
        RecognizePlateArgs, \
        RecognizePlateFromPathArgs, \
        DetectAndRecognizePlateArgs, \
        DetectAndRecognizePlateFromPathArgs

    class RecognizePlateArgs(BaseModel):
        """Input arguments for recognizing text from a license plate image."""

        model_config = ConfigDict(extra="forbid")
        image_base64: Base64ImageStr
        ocr_model: OcrModel = Field(default=settings.default_ocr_model)

    class RecognizePlateFromPathArgs(BaseModel):
        """Input arguments for recognizing text from a license plate image path."""

        model_config = ConfigDict(extra="forbid")
        path: str = Field(..., examples=["https://example.com/plate.jpg"])
        ocr_model: OcrModel = Field(default=settings.default_ocr_model)

        @field_validator("path")
        @classmethod
        def path_must_not_be_empty(cls, v: str) -> str:
            if not v or not v.strip():
                raise ValueError("Path cannot be empty.")
            return v

    class DetectAndRecognizePlateArgs(BaseModel):
        """Input arguments for detecting and recognizing a license plate from an image."""

        model_config = ConfigDict(extra="forbid")
        image_base64: Base64ImageStr
        detector_model: DetectorModel = Field(default=settings.default_detector_model)
        ocr_model: OcrModel = Field(default=settings.default_ocr_model)

    class DetectAndRecognizePlateFromPathArgs(BaseModel):
        """Input arguments for detecting and recognizing a license plate from a path."""

        model_config = ConfigDict(extra="forbid")
        path: str = Field(..., examples=["https://example.com/car.jpg"])
        detector_model: DetectorModel = Field(default=settings.default_detector_model)
        ocr_model: OcrModel = Field(default=settings.default_ocr_model)

        @field_validator("path")
        @classmethod
        def path_must_not_be_empty(cls, v: str) -> str:
            if not v or not v.strip():
                raise ValueError("Path cannot be empty.")
            return v

    # --- Tool Registration ---

    # Tool 1: recognize_plate
    recognize_plate_tool_definition = types.Tool(
        name="recognize_plate",
        title="Recognize License Plate",
        description="Recognizes text from a pre-cropped image of a license plate.",
        inputSchema=RecognizePlateArgs.model_json_schema(),
    )
    tool_registry.register_tool(
        tool_definition=recognize_plate_tool_definition,
        model=RecognizePlateArgs,
        func=recognize_plate_base64_tool,
    )

    # Tool 2: recognize_plate_from_path
    recognize_plate_from_path_tool_definition = types.Tool(
        name="recognize_plate_from_path",
        title="Recognize License Plate from Path",
        description="Recognizes text from a pre-cropped license plate image located at a given URL or local file path.",
        inputSchema=RecognizePlateFromPathArgs.model_json_schema(),
    )
    tool_registry.register_tool(
        tool_definition=recognize_plate_from_path_tool_definition,
        model=RecognizePlateFromPathArgs,
        func=recognize_plate_path_tool,
    )

    # Tool 3: detect_and_recognize_plate
    detect_and_recognize_plate_tool_definition = types.Tool(
        name="detect_and_recognize_plate",
        title="Detect and Recognize License Plate",
        description="Detects and recognizes all license plates available in an image.",
        inputSchema=DetectAndRecognizePlateArgs.model_json_schema(),
    )
    tool_registry.register_tool(
        tool_definition=detect_and_recognize_plate_tool_definition,
        model=DetectAndRecognizePlateArgs,
        func=detect_and_recognize_plate_base64_tool,
    )

    # Tool 4: detect_and_recognize_plate_from_path
    detect_and_recognize_plate_from_path_tool_definition = types.Tool(
        name="detect_and_recognize_plate_from_path",
        title="Detect and Recognize License Plate from Path",
        description="Detects and recognizes license plates in an image at a given URL or local file path.",
        inputSchema=DetectAndRecognizePlateFromPathArgs.model_json_schema(),
    )
    tool_registry.register_tool(
        tool_definition=detect_and_recognize_plate_from_path_tool_definition,
        model=DetectAndRecognizePlateFromPathArgs,
        func=detect_and_recognize_plate_path_tool,
    )

    # Tool 5: list_models
    list_models_tool_definition = types.Tool(
        name="list_models",
        title="List Available Models",
        description="Lists the available detector and OCR models.",
        inputSchema=ListModelsArgs.model_json_schema(),
    )
    tool_registry.register_tool(
        tool_definition=list_models_tool_definition,
        model=ListModelsArgs,
        func=list_models,
    )
