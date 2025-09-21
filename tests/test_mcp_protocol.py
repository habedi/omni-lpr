import pytest


@pytest.mark.asyncio
async def test_mcp_post_endpoint_invalid_payload(test_app_client):
    """
    Posting an invalid payload to the MCP endpoint should result in a client error.
    We accept any 4xx response here to confirm the route is wired correctly.
    """
    # Note: Added trailing slash to URL to avoid 307 redirect
    # Empty body
    resp = await test_app_client.post("/mcp/", content="")
    assert 400 <= resp.status_code < 500

    # Invalid JSON
    resp = await test_app_client.post(
        "/mcp/",
        headers={"Content-Type": "application/json"},
        content="{not: valid}",
    )
    assert 400 <= resp.status_code < 500


@pytest.mark.asyncio
async def test_mcp_get_endpoint_for_session(test_app_client):
    """
    A GET request without a session ID should be handled gracefully.
    The MCP server should respond with a 4xx error if the session is not found.
    """
    # Note: Added trailing slash to URL to avoid the HTTP 307 redirect
    resp = await test_app_client.get("/mcp/")
    assert 400 <= resp.status_code < 500
