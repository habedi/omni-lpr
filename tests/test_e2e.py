import pytest
from httpx import AsyncClient

# This image is from https://free-images.com/display/deadman_ranch_ancient_buildings_10.html
# and is marked as Public Domain CC0.
IMAGE_URL = "https://free-images.com/lg/ba26/deadman_ranch_ancient_buildings_10.jpg"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_detect_and_recognize_plate_from_path_e2e(test_app_client: AsyncClient):
    """
    End-to-end test for the 'detect_and_recognize_plate_from_path' tool.
    This test uses a real-world image from a URL and expects a successful detection.
    """
    response = await test_app_client.post(
        "/api/v1/tools/detect_and_recognize_plate_from_path/invoke",
        json={
            "path": IMAGE_URL,
            "ocr_model": "cct-xs-v1-global-model",
            "detector_model": "yolo-v9-t-384-license-plate-end2end",
        },
    )

    assert response.status_code == 200, f"Request failed: {response.text}"
    response_json = response.json()
    content = response_json["content"][0]["data"]

    # The image contains multiple license plates. We expect the tool to find at least one.
    assert len(content) > 0
    # Check that the first result has the expected structure.
    assert "ocr" in content[0]
    assert "text" in content[0]["ocr"]
    assert "confidence" in content[0]["ocr"]
    assert "detection" in content[0]
    assert "bounding_box" in content[0]["detection"]
    assert "confidence" in content[0]["detection"]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_no_plate_detection_e2e(test_app_client: AsyncClient):
    """
    Tests that the 'detect_and_recognize_plate_from_path' tool returns an
    empty list when given an image without a license plate.
    """
    # This is a public domain image of a landscape from Wikimedia Commons.
    image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/9/91/Peyto_Lake-Banff_NP-Canada.jpg/500px-Peyto_Lake-Banff_NP-Canada.jpg"
    response = await test_app_client.post(
        "/api/v1/tools/detect_and_recognize_plate_from_path/invoke",
        json={
            "path": image_url,
            "ocr_model": "cct-xs-v1-global-model",
            "detector_model": "yolo-v9-t-384-license-plate-end2end",
        },
    )

    assert response.status_code == 200, f"Request failed: {response.text}"
    response_json = response.json()
    content = response_json["content"][0]["data"]
    assert content == []
