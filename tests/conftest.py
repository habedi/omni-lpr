import pytest
from httpx import ASGITransport, AsyncClient

from omni_lpr.__main__ import setup_app_routes, setup_tools, starlette_app
from omni_lpr.tools import tool_registry


@pytest.fixture
async def test_app_client():
    """
    Provides a configured test client for the Starlette application.
    This fixture ensures a clean state for each test function.
    """
    # Clear any previously registered tools to ensure a clean state
    tool_registry._tools.clear()
    tool_registry._tool_definitions.clear()
    tool_registry._tool_models.clear()

    # Clear existing routes from previous tests
    starlette_app.routes.clear()

    # Set up the application components
    setup_tools()
    setup_app_routes(starlette_app)

    # Yield a test client
    async with AsyncClient(transport=ASGITransport(app=starlette_app),
                           base_url="http://test") as client:
        yield client


@pytest.fixture
async def no_tools_test_app_client():
    """
    Provides a test client where no tools have been registered.
    """
    # Clear any previously registered tools
    tool_registry._tools.clear()
    tool_registry._tool_definitions.clear()
    tool_registry._tool_models.clear()

    # Clear existing routes
    starlette_app.routes.clear()

    # Set up routes WITHOUT setting up tools
    setup_app_routes(starlette_app)

    async with AsyncClient(transport=ASGITransport(app=starlette_app),
                           base_url="http://test") as client:
        yield client
