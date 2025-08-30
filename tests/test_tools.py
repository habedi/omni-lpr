import json
from dataclasses import asdict, dataclass
from typing import get_args
from unittest.mock import AsyncMock, MagicMock

import pytest
from mcp import types
from omni_lpr import tools
from omni_lpr.errors import ErrorCode, ToolLogicError
from omni_lpr.tools import (
    DetectorModel,
    ListModelsArgs,
    OcrModel,
    ToolRegistry,
    list_models,
    setup_tools,
    tool_registry as global_tool_registry,
)
from pydantic import BaseModel

TINY_PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="


@dataclass
class MockBoundingBox:
    x1: int
    y1: int
    x2: int
    y2: int


@dataclass
class MockDetectionResult:
    bounding_box: MockBoundingBox
    confidence: float


@dataclass
class MockOcrResult:
    text: str
    confidence: float


@dataclass
class MockALPRResult:
    detection: MockDetectionResult
    ocr: MockOcrResult


@pytest.fixture
def mock_alpr_result():
    return MockALPRResult(
        detection=MockDetectionResult(
            bounding_box=MockBoundingBox(x1=10, y1=20, x2=100, y2=50), confidence=0.99
        ),
        ocr=MockOcrResult(text="TEST1234", confidence=0.95),
    )


@pytest.fixture(autouse=True)
def clear_caches_and_registry():
    """Clears all tool-related caches and the global registry before each test."""
    tools._ocr_model_cache.clear()
    tools._alpr_cache.clear()
    global_tool_registry._tools.clear()
    global_tool_registry._tool_definitions.clear()
    global_tool_registry._tool_models.clear()
    # Also clear the global placeholder models
    tools.RecognizePlateArgs = BaseModel
    tools.RecognizePlateFromPathArgs = BaseModel
    tools.DetectAndRecognizePlateArgs = BaseModel
    tools.DetectAndRecognizePlateFromPathArgs = BaseModel


@pytest.fixture
def tool_registry(mocker):
    """Provides a fresh ToolRegistry instance for isolated tests."""
    registry = ToolRegistry()
    mocker.patch("omni_lpr.tools.tool_registry", registry)
    return registry


def test_register_and_list_tools(tool_registry: ToolRegistry):
    tool_definition = types.Tool(
        name="test_tool",
        title="Test Tool",
        description="A tool for testing.",
        inputSchema={"type": "object", "properties": {}},
    )

    class TestArgs(BaseModel):
        pass

    @tool_registry.register(tool_definition, TestArgs)
    async def test_tool(_: TestArgs):
        return [types.TextContent(type="text", text="success")]

    listed_tools = tool_registry.list()
    assert len(listed_tools) == 1
    assert listed_tools[0] == tool_definition


@pytest.mark.asyncio
async def test_call_tool_success(tool_registry: ToolRegistry):
    class TestArgs(BaseModel):
        message: str

    tool_definition = types.Tool(
        name="test_tool",
        title="Test",
        description="A test",
        inputSchema=TestArgs.model_json_schema(),
    )

    @tool_registry.register(tool_definition, TestArgs)
    async def test_tool(args: TestArgs):
        return [types.TextContent(type="text", text=args.message)]

    result = await tool_registry.call("test_tool", {"message": "hello"})
    assert len(result) == 1
    assert isinstance(result[0], types.TextContent)
    assert result[0].text == "hello"


@pytest.mark.asyncio
async def test_call_tool_validation_error(tool_registry: ToolRegistry):
    class TestArgs(BaseModel):
        message: str

    tool_definition = types.Tool(
        name="test_tool",
        title="Test",
        description="A test",
        inputSchema=TestArgs.model_json_schema(),
    )

    @tool_registry.register(tool_definition, TestArgs)
    async def test_tool(args: TestArgs):
        return [types.TextContent(type="text", text=args.message)]

    with pytest.raises(ToolLogicError, match="Input validation failed"):
        await tool_registry.call("test_tool", {"wrong_arg": "hello"})


@pytest.mark.asyncio
async def test_call_unknown_tool(tool_registry: ToolRegistry):
    with pytest.raises(ToolLogicError, match="Unknown tool: unknown_tool"):
        await tool_registry.call("unknown_tool", {})


@pytest.mark.asyncio
async def test_recognize_plate_base64_tool_success(mocker):
    setup_tools()
    mocker.patch("anyio.to_thread.run_sync", return_value=["TEST-123"])
    mock_get_image = mocker.patch(
        "omni_lpr.tools._get_image_from_source", return_value=AsyncMock()
    )
    mocker.patch("omni_lpr.tools._get_ocr_recognizer", return_value=AsyncMock())

    result = await global_tool_registry.call(
        "recognize_plate", {"image_base64": TINY_PNG_BASE64}
    )

    assert json.loads(result[0].text) == ["TEST-123"]
    mock_get_image.assert_called_once_with(image_base64=TINY_PNG_BASE64, path=None)


@pytest.mark.asyncio
async def test_recognize_plate_path_tool_success(mocker):
    setup_tools()
    mocker.patch("anyio.to_thread.run_sync", return_value=["TEST-123"])
    mock_get_image = mocker.patch(
        "omni_lpr.tools._get_image_from_source", return_value=AsyncMock()
    )
    mocker.patch("omni_lpr.tools._get_ocr_recognizer", return_value=AsyncMock())

    result = await global_tool_registry.call(
        "recognize_plate_from_path", {"path": "/fake/path.jpg"}
    )

    assert json.loads(result[0].text) == ["TEST-123"]
    mock_get_image.assert_called_once_with(image_base64=None, path="/fake/path.jpg")


@pytest.mark.asyncio
async def test_detect_and_recognize_plate_base64_tool_success(mocker, mock_alpr_result):
    setup_tools()
    mocker.patch("anyio.to_thread.run_sync", return_value=[mock_alpr_result])
    mock_get_image = mocker.patch(
        "omni_lpr.tools._get_image_from_source", return_value=AsyncMock()
    )
    mocker.patch("omni_lpr.tools._get_alpr_instance", return_value=AsyncMock())

    result = await global_tool_registry.call(
        "detect_and_recognize_plate", {"image_base64": TINY_PNG_BASE64}
    )

    expected_dict = [asdict(mock_alpr_result)]
    assert json.loads(result[0].text) == expected_dict
    mock_get_image.assert_called_once_with(image_base64=TINY_PNG_BASE64, path=None)


@pytest.mark.asyncio
async def test_detect_and_recognize_plate_path_tool_success(mocker, mock_alpr_result):
    setup_tools()
    mocker.patch("anyio.to_thread.run_sync", return_value=[mock_alpr_result])
    mock_get_image = mocker.patch(
        "omni_lpr.tools._get_image_from_source", return_value=AsyncMock()
    )
    mocker.patch("omni_lpr.tools._get_alpr_instance", return_value=AsyncMock())

    result = await global_tool_registry.call(
        "detect_and_recognize_plate_from_path", {"path": "/fake/path.jpg"}
    )

    expected_dict = [asdict(mock_alpr_result)]
    assert json.loads(result[0].text) == expected_dict
    mock_get_image.assert_called_once_with(image_base64=None, path="/fake/path.jpg")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_name, invalid_data, expected_error_msg",
    [
        ("recognize_plate", {"image_base64": ""}, "image_base64 cannot be empty"),
        (
            "recognize_plate",
            {"image_base64": "a" * 7000001},
            "Input image is too large",
        ),
        ("recognize_plate", {"image_base64": "not-base64"}, "Invalid base64 string"),
        ("recognize_plate_from_path", {"path": " "}, "Path cannot be empty"),
        (
            "recognize_plate",
            {"image_base64": TINY_PNG_BASE64, "path": "/path"},
            "Extra inputs are not permitted",
        ),
        ("recognize_plate", {}, "Field required"),
    ],
)
async def test_tool_validation_errors(tool_name, invalid_data, expected_error_msg):
    setup_tools()
    with pytest.raises(ToolLogicError) as excinfo:
        await global_tool_registry.call(tool_name, invalid_data)

    assert excinfo.value.error.code == ErrorCode.VALIDATION_ERROR
    assert expected_error_msg in str(excinfo.value.error.details)


@pytest.mark.asyncio
async def test_recognizer_model_caching(mocker):
    setup_tools()
    mock_recognizer_instance = MagicMock()
    mock_recognizer_instance.run.return_value = ["CACHED"]
    mock_recognizer_class = mocker.patch(
        "fast_plate_ocr.LicensePlateRecognizer", return_value=mock_recognizer_instance
    )
    mocker.patch("omni_lpr.tools._get_image_from_source", return_value=AsyncMock())

    # Call tool with first OCR model
    await global_tool_registry.call(
        "recognize_plate",
        {"image_base64": TINY_PNG_BASE64, "ocr_model": "cct-s-v1-global-model"},
    )
    # Call it again, should be cached
    await global_tool_registry.call(
        "recognize_plate",
        {"image_base64": TINY_PNG_BASE64, "ocr_model": "cct-s-v1-global-model"},
    )
    mock_recognizer_class.assert_called_once_with("cct-s-v1-global-model")

    # Call tool with second OCR model
    await global_tool_registry.call(
        "recognize_plate",
        {"image_base64": TINY_PNG_BASE64, "ocr_model": "cct-xs-v1-global-model"},
    )
    assert mock_recognizer_class.call_count == 2


@pytest.mark.asyncio
async def test_alpr_instance_caching(mocker):
    setup_tools()
    mock_alpr_instance = MagicMock()
    mock_alpr_instance.predict.return_value = []
    mock_alpr_class = mocker.patch("fast_alpr.ALPR", return_value=mock_alpr_instance)
    mocker.patch("omni_lpr.tools._get_image_from_source", return_value=AsyncMock())

    # Call with first set of models
    args_1 = {
        "image_base64": TINY_PNG_BASE64,
        "detector_model": "yolo-v9-t-384-license-plate-end2end",
        "ocr_model": "cct-s-v1-global-model",
    }
    await global_tool_registry.call("detect_and_recognize_plate", args_1)
    await global_tool_registry.call("detect_and_recognize_plate", args_1)
    mock_alpr_class.assert_called_once_with(
        detector_model="yolo-v9-t-384-license-plate-end2end",
        ocr_model="cct-s-v1-global-model",
    )

    # Call with second set of models
    args_2 = {
        "image_base64": TINY_PNG_BASE64,
        "detector_model": "yolo-v9-t-256-license-plate-end2end",
        "ocr_model": "cct-xs-v1-global-model",
    }
    await global_tool_registry.call("detect_and_recognize_plate", args_2)
    assert mock_alpr_class.call_count == 2


@pytest.mark.asyncio
async def test_list_models():
    result = await list_models(ListModelsArgs())
    assert len(result) == 1
    assert isinstance(result[0], types.TextContent)
    models = json.loads(result[0].text)
    expected = {
        "detector_models": list(get_args(DetectorModel)),
        "ocr_models": list(get_args(OcrModel)),
    }
    assert models == expected
