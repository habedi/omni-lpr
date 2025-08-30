import pytest


@pytest.mark.asyncio
async def test_health_check(test_app_client):
    """Test the health check endpoint."""
    response = await test_app_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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
    assert "input_schema" in detect_tool
    assert "image_base64" in detect_tool["input_schema"]["properties"]


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
    assert "detector_models" in data[0]
    assert "ocr_models" in data[0]
