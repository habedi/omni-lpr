import pytest

from omni_lpr.mcp import call_tool_handler, list_tools_handler


@pytest.mark.asyncio
async def test_mcp_list_tools_handler(mocker):
    mock_list = mocker.patch("omni_lpr.tools.tool_registry.list", return_value=["tool1", "tool2"])
    res = await list_tools_handler()
    assert res == ["tool1", "tool2"]
    mock_list.assert_called_once()


@pytest.mark.asyncio
async def test_mcp_call_tool_handler(mocker):
    mock_call = mocker.patch("omni_lpr.tools.tool_registry.call", return_value=["result"])
    res = await call_tool_handler("test-tool", {"arg": "val"})
    assert res == ["result"]
    mock_call.assert_called_once_with("test-tool", {"arg": "val"})
