import base64
import json
from dataclasses import asdict, dataclass
from typing import get_args
from unittest.mock import AsyncMock, MagicMock

import pytest
from mcp import types
from pydantic import BaseModel

from omni_lpr import tools
from omni_lpr.errors import ErrorCode, ToolLogicError
from omni_lpr.tools import (
    DetectAndRecognizePlateArgs,
    DetectAndRecognizePlateFromPathArgs,
    DetectorModel,
    ListModelsArgs,
    OcrModel,
    RecognizePlateArgs,
    RecognizePlateFromPathArgs,
    ToolRegistry,
    detect_and_recognize_plate,
    detect_and_recognize_plate_from_path,
    list_models,
    recognize_plate,
    recognize_plate_from_path,
)

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
def clear_caches():
    tools._ocr_model_cache.clear()
    tools._alpr_cache.clear()


@pytest.fixture
def tool_registry():
    return ToolRegistry()


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

    tools = tool_registry.list()
    assert len(tools) == 1
    assert tools[0] == tool_definition


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
async def test_recognize_plate_success(mocker):
    mock_recognizer_instance = MagicMock()
    mock_recognizer_instance.run.return_value = ["TEST-123"]
    mocker.patch(
        "fast_plate_ocr.LicensePlateRecognizer", return_value=mock_recognizer_instance
    )
    args = RecognizePlateArgs(image_base64=TINY_PNG_BASE64)

    result = await recognize_plate(args)

    assert json.loads(result[0].text) == ["TEST-123"]
    mock_recognizer_instance.run.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_data, expected_error_msg",
    [
        ({"image_base64": "a" * 7000001}, "Input image is too large"),
        ({"image_base64": "not-base64"}, "Invalid base64 string"),
        ({"image_base64": ""}, "image_base64 cannot be empty"),
        (
                {"image_base64": TINY_PNG_BASE64, "model_name": "invalid-model"},
                "Extra inputs are not permitted",
        ),
    ],
)
async def test_recognize_plate_validation(tool_registry, invalid_data, expected_error_msg):
    recognize_plate_tool_definition = types.Tool(
        name="recognize_plate",
        title="Recognize Plate",
        description="A test tool for recognizing plates.",
        inputSchema=RecognizePlateArgs.model_json_schema(),
    )
    tool_registry.register(recognize_plate_tool_definition, RecognizePlateArgs)(AsyncMock())

    with pytest.raises(ToolLogicError) as excinfo:
        await tool_registry.call("recognize_plate", invalid_data)

    assert excinfo.value.error.code == ErrorCode.VALIDATION_ERROR
    assert expected_error_msg in str(excinfo.value.error.details)


@pytest.mark.asyncio
async def test_recognize_plate_from_path_url_success(mocker):
    mock_recognizer_instance = MagicMock()
    mock_recognizer_instance.run.return_value = ["URL-TEST"]
    mocker.patch(
        "fast_plate_ocr.LicensePlateRecognizer", return_value=mock_recognizer_instance
    )

    image_bytes = base64.b64decode(TINY_PNG_BASE64)
    mock_response = AsyncMock()
    mock_response.aread.return_value = image_bytes
    mock_response.raise_for_status = MagicMock()

    mock_async_client = AsyncMock()
    mock_async_client.get.return_value = mock_response
    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_async_client
    mocker.patch("httpx.AsyncClient", return_value=mock_cm)

    args = RecognizePlateFromPathArgs(path="http://fake.url/plate.jpg")
    result = await recognize_plate_from_path(args)

    assert json.loads(result[0].text) == ["URL-TEST"]
    mock_async_client.get.assert_called_once_with("http://fake.url/plate.jpg")


@pytest.mark.asyncio
async def test_recognize_plate_from_path_file_success(mocker):
    mock_recognizer_instance = MagicMock()
    mock_recognizer_instance.run.return_value = ["FILE-TEST"]
    mocker.patch(
        "fast_plate_ocr.LicensePlateRecognizer", return_value=mock_recognizer_instance
    )
    image_bytes = base64.b64decode(TINY_PNG_BASE64)
    mocker.patch("anyio.Path.read_bytes", new_callable=AsyncMock, return_value=image_bytes)

    args = RecognizePlateFromPathArgs(path="/fake/path/plate.jpg")
    result = await recognize_plate_from_path(args)

    assert json.loads(result[0].text) == ["FILE-TEST"]


@pytest.mark.asyncio
async def test_detect_and_recognize_plate_success(mocker, mock_alpr_result):
    mock_alpr_instance = MagicMock()
    mock_alpr_instance.predict.return_value = [mock_alpr_result]
    mocker.patch("fast_alpr.ALPR", return_value=mock_alpr_instance)

    args = DetectAndRecognizePlateArgs(image_base64=TINY_PNG_BASE64)
    result = await detect_and_recognize_plate(args)

    expected_dict = [asdict(mock_alpr_result)]
    assert json.loads(result[0].text) == expected_dict
    mock_alpr_instance.predict.assert_called_once()


@pytest.mark.asyncio
async def test_detect_and_recognize_plate_from_path_url_success(mocker, mock_alpr_result):
    mock_alpr_instance = MagicMock()
    mock_alpr_instance.predict.return_value = [mock_alpr_result]
    mocker.patch("fast_alpr.ALPR", return_value=mock_alpr_instance)

    image_bytes = base64.b64decode(TINY_PNG_BASE64)
    mock_response = AsyncMock()
    mock_response.aread.return_value = image_bytes
    mock_response.raise_for_status = MagicMock()
    mock_async_client = AsyncMock()
    mock_async_client.get.return_value = mock_response
    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_async_client
    mocker.patch("httpx.AsyncClient", return_value=mock_cm)

    args = DetectAndRecognizePlateFromPathArgs(path="http://fake.url/image.png")
    result = await detect_and_recognize_plate_from_path(args)

    expected_dict = [asdict(mock_alpr_result)]
    assert json.loads(result[0].text) == expected_dict


@pytest.mark.asyncio
async def test_detect_and_recognize_plate_from_path_file_success(mocker, mock_alpr_result):
    mock_alpr_instance = MagicMock()
    mock_alpr_instance.predict.return_value = [mock_alpr_result]
    mocker.patch("fast_alpr.ALPR", return_value=mock_alpr_instance)

    args = DetectAndRecognizePlateFromPathArgs(path="/fake/path/image.png")
    await detect_and_recognize_plate_from_path(args)

    mock_alpr_instance.predict.assert_called_once_with("/fake/path/image.png")


@pytest.mark.asyncio
async def test_recognizer_model_caching(mocker):
    mock_recognizer_instance = MagicMock()
    mock_recognizer_instance.run.return_value = ["CACHED"]
    mock_recognizer_class = mocker.patch(
        "fast_plate_ocr.LicensePlateRecognizer", return_value=mock_recognizer_instance
    )

    args_a = RecognizePlateArgs(
        image_base64=TINY_PNG_BASE64, ocr_model="cct-s-v1-global-model"
    )
    args_b = RecognizePlateArgs(
        image_base64=TINY_PNG_BASE64, ocr_model="cct-xs-v1-global-model"
    )

    await recognize_plate(args_a)
    await recognize_plate(args_a)
    mock_recognizer_class.assert_called_once_with("cct-s-v1-global-model")

    await recognize_plate(args_b)
    assert mock_recognizer_class.call_count == 2


@pytest.mark.asyncio
async def test_alpr_instance_caching(mocker):
    mock_alpr_instance = MagicMock()
    mock_alpr_instance.predict.return_value = []
    mock_alpr_class = mocker.patch("fast_alpr.ALPR", return_value=mock_alpr_instance)

    args_1 = DetectAndRecognizePlateArgs(
        image_base64=TINY_PNG_BASE64,
        detector_model="yolo-v9-t-384-license-plate-end2end",
        ocr_model="cct-s-v1-global-model",
    )
    args_2 = DetectAndRecognizePlateArgs(
        image_base64=TINY_PNG_BASE64,
        detector_model="yolo-v9-t-256-license-plate-end2end",
        ocr_model="cct-xs-v1-global-model",
    )

    await detect_and_recognize_plate(args_1)
    await detect_and_recognize_plate(args_1)
    mock_alpr_class.assert_called_once_with(
        detector_model="yolo-v9-t-384-license-plate-end2end",
        ocr_model="cct-s-v1-global-model",
    )

    await detect_and_recognize_plate(args_2)
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
