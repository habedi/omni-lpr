import pytest


@pytest.mark.asyncio
async def test_health_check():
    from omni_lpr.__main__ import setup_app_routes, setup_tools, starlette_app
    from httpx import ASGITransport, AsyncClient

    # Manually set up the app for testing
    setup_tools()
    setup_app_routes(starlette_app)

    async with AsyncClient(
        transport=ASGITransport(app=starlette_app), base_url="http://test"
    ) as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
