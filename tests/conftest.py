# File: tests/conftest.py

from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.types import Receive, Scope, Send

# Import what we need to build the app, but not the app instances themselves
from omni_lpr.event_store import InMemoryEventStore
from omni_lpr.mcp import app as mcp_app
from omni_lpr.rest import api_spec, setup_rest_routes
from omni_lpr.tools import setup_cache, setup_tools, tool_registry


@pytest.fixture
def test_data_path():
    """Returns the path to the test data directory."""
    return Path(__file__).parent / "testdata"


def create_test_app(with_tools: bool = True) -> Starlette:
    """
    Factory function to create a fully isolated app instance for testing.
    This includes creating a new session manager for each app.
    """
    # 1. Create a new session manager for this specific test app
    event_store = InMemoryEventStore()
    session_manager = StreamableHTTPSessionManager(app=mcp_app, event_store=event_store)

    # 2. Define lifespan and handlers that close over the new session manager
    @asynccontextmanager
    async def lifespan(app: Starlette):
        async with session_manager.run():
            yield

    async def handle_streamable_http(scope: Scope, receive: Receive, send: Send) -> None:
        await session_manager.handle_request(scope, receive, send)

    # 3. Create a fresh Starlette app with the isolated lifespan
    app = Starlette(debug=True, lifespan=lifespan)

    # 4. Manage tool registry state based on test type
    if with_tools:
        tool_registry._tools.clear()
        tool_registry._tool_definitions.clear()
        tool_registry._tool_models.clear()
        setup_tools()
        setup_cache()
    else:
        tool_registry._tools.clear()
        tool_registry._tool_definitions.clear()
        tool_registry._tool_models.clear()

    # 5. Set up routes on the isolated app
    # We need to re-import the health_check to avoid scope issues
    from omni_lpr.__main__ import health_check

    health_route = Route("/api/health", endpoint=health_check, methods=["GET"])
    app.routes.extend(
        [
            Mount("/mcp/", app=handle_streamable_http),
            health_route,
            Mount("/api/v1", routes=setup_rest_routes()),
        ]
    )
    api_spec.register(app)
    return app


@pytest.fixture
async def test_app_client():
    """
    Provides a configured test client that correctly handles the ASGI lifespan.
    """
    app = create_test_app(with_tools=True)
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client


@pytest.fixture
async def no_tools_test_app_client():
    """
    Provides a test client where no tools have been registered.
    """
    app = create_test_app(with_tools=False)
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
