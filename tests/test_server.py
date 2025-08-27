import pytest


@pytest.mark.asyncio
async def test_health_check():
    from server.__main__ import starlette_app
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=starlette_app), base_url="http://test"
    ) as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
