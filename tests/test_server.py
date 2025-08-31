import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_health_check(test_app_client):
    """Test the health check endpoint."""
    response = await test_app_client.get("/api/health")
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["status"] == "ok"
    assert "version" in response_json


@pytest.mark.asyncio
async def test_list_tools_with_no_tools(no_tools_test_app_client):
    """Test the GET /tools endpoint when no tools are registered."""
    response = await no_tools_test_app_client.get("/api/v1/tools")
    assert response.status_code == 200
    response_json = response.json()
    assert response_json == {"tools": []}


@pytest.mark.asyncio
async def test_list_tools_endpoint(test_app_client):
    """Test the GET /tools endpoint."""
    response = await test_app_client.get("/api/v1/tools")
    assert response.status_code == 200
    response_json = response.json()
    assert "tools" in response_json
    assert isinstance(response_json["tools"], list)
    # Check for a known tool
    detect_tool = next(
        (t for t in response_json["tools"] if t["name"] == "detect_and_recognize_plate"),
        None,
    )
    assert detect_tool is not None
    assert detect_tool["title"] == "Detect and Recognize License Plate"
    assert "inputSchema" in detect_tool
    assert "image_base64" in detect_tool["inputSchema"]["properties"]


@pytest.mark.asyncio
async def test_tool_invocation_endpoint(test_app_client):
    """Test the POST /tools/{tool_name}/invoke endpoint."""
    response = await test_app_client.post("/api/v1/tools/list_models/invoke", json={})
    assert response.status_code == 200
    response_json = response.json()
    assert "content" in response_json
    assert isinstance(response_json["content"], list)
    assert response_json["content"][0]["type"] == "json"
    data = response_json["content"][0]["data"]
    assert "detector_models" in data
    assert "ocr_models" in data


@pytest.mark.asyncio
async def test_tool_invocation_with_empty_body(test_app_client):
    """Test invoking a tool with an empty request body."""
    response = await test_app_client.post(
        "/api/v1/tools/list_models/invoke", content="", headers={"Content-Length": "0"}
    )
    assert response.status_code == 200
    response_json = response.json()
    assert "content" in response_json
    data = response_json["content"][0]["data"]
    assert "detector_models" in data


@pytest.mark.asyncio
async def test_tool_invocation_with_multipart_form_data(test_app_client, test_data_path, mocker):
    """Test invoking a tool with a multipart/form-data request (file upload)."""
    # Mock the actual model loading and processing
    mocker.patch("anyio.to_thread.run_sync", return_value=["MOCKED-RESULT"])
    mocker.patch("omni_lpr.tools._get_image_from_source", new_callable=AsyncMock)
    mocker.patch("omni_lpr.tools._get_ocr_recognizer")

    image_path = test_data_path / "dummy_image.png"
    image_bytes = image_path.read_bytes()

    files = {"image": ("dummy_image.png", image_bytes, "image/png")}
    data = {"ocr_model": "cct-s-v1-global-model"}
    response = await test_app_client.post(
        "/api/v1/tools/recognize_plate/invoke", files=files, data=data
    )

    assert response.status_code == 200, f"Request failed: {response.text}"
    response_json = response.json()
    assert "content" in response_json
    assert response_json["content"][0]["type"] == "json"
    result_data = response_json["content"][0]["data"]
    assert result_data == ["MOCKED-RESULT"]
