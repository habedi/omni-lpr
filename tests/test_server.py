import pytest


@pytest.mark.asyncio
async def test_health_check(test_app_client):
    """Test the health check endpoint."""
    response = await test_app_client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_list_models_endpoint(test_app_client):
    """Test the list_models REST endpoint."""
    # The endpoint is created via create_rest_endpoint, so it's a POST
    response = await test_app_client.post("/api/list_models", json={})

    assert response.status_code == 200
    expected_structure = {
        "results": [
            {
                "detector_models": [
                    "yolo-v9-s-608-license-plate-end2end",
                    "yolo-v9-t-640-license-plate-end2end",
                    "yolo-v9-t-512-license-plate-end2end",
                    "yolo-v9-t-416-license-plate-end2end",
                    "yolo-v9-t-384-license-plate-end2end",
                    "yolo-v9-t-256-license-plate-end2end",
                ],
                "ocr_models": ["cct-s-v1-global-model", "cct-xs-v1-global-model"],
            }
        ]
    }
    assert response.json() == expected_structure
