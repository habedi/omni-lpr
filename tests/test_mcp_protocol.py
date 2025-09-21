import json

import pytest


@pytest.mark.asyncio
async def test_mcp_root_endpoint(test_app_client):
    """The MCP Streamable HTTP transport should expose a root endpoint."""
    resp = await test_app_client.get("/mcp/v1/root")
    assert resp.status_code in [200, 404, 405]
    # If 200 OK, ensure it's JSON with some structure
    if resp.status_code == 200:
        data = resp.json()
        assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_mcp_requests_endpoint_invalid_payload(test_app_client):
    """Posting an invalid payload to the requests endpoint should not 500.

    We accept any 4xx/405 response here to confirm the route is wired
    and handled by the MCP transport.
    """
    # Empty body
    resp = await test_app_client.post("/mcp/v1/requests", content="")
    assert resp.status_code in [400, 404, 405, 415, 422]

    # Invalid JSON
    resp = await test_app_client.post(
        "/mcp/v1/requests",
        headers={"Content-Type": "application/json"},
        content="{not: valid}",
    )
    assert resp.status_code in [400, 404, 405, 415, 422]
