"""Unit tests for Tool Registry, Tool Contracts, and Policy Engine."""

import pytest
from app.tools.registry import tool_registry
from app.tools.system.current_time import CurrentTimeTool


def test_tool_registry_initialization():
    """Verify tool registry initializes with registered tools."""
    tools = tool_registry.get_all_tools()
    assert len(tools) == 15

    schemas = tool_registry.get_deepgram_function_schemas()
    assert len(schemas) == 15
    for s in schemas:
        assert "name" in s
        assert "description" in s
        assert "parameters" in s


def test_tool_metadata_contract():
    """Verify Tool Registration Contract adheres to explicit metadata schema."""
    catalog = tool_registry.get_metadata_catalog()
    assert len(catalog) == 15

    for meta in catalog:
        assert "name" in meta
        assert "description" in meta
        assert "capability" in meta
        assert "read_only" in meta
        assert "requires_confirmation" in meta
        assert "timeout_seconds" in meta
        assert "parameters" in meta


def test_capability_routing_subsets():
    """Verify capability-based tool filtering."""
    email_tools = tool_registry.get_tools_by_capability("email")
    assert len(email_tools) == 2
    assert {t.name for t in email_tools} == {"send_email", "search_emails"}

    scoped_schemas = tool_registry.get_deepgram_function_schemas(capabilities=["calendar"])
    # calendar tools (2) + system tools (3: get_current_time, end_voice_session, get_connected_apps)
    assert len(scoped_schemas) == 5


@pytest.mark.asyncio
async def test_write_action_confirmation_policy():
    """Verify write tools require verbal confirmation before executing."""
    # 1. Unconfirmed attempt -> should halt and propose action
    unconfirmed_res = await tool_registry.execute_tool(
        "send_email",
        {"recipient": "john@example.com", "subject": "Quarterly Report", "body": "Attached."},
        confirmed=False,
    )
    assert unconfirmed_res["requires_confirmation"] is True
    assert "Should I send it now?" in unconfirmed_res["spoken_summary"]

    # 2. Confirmed attempt -> executes
    confirmed_res = await tool_registry.execute_tool(
        "send_email",
        {"recipient": "john@example.com", "subject": "Quarterly Report", "body": "Attached."},
        confirmed=True,
    )
    assert confirmed_res.get("success") is True


@pytest.mark.asyncio
async def test_current_time_tool():
    """Verify current time tool execution."""
    tool = CurrentTimeTool()
    assert tool.read_only is True
    assert tool.requires_confirmation is False
    res = await tool.execute(timezone="UTC")
    assert res["success"] is True
    assert "It is currently" in res["spoken_time"]


@pytest.mark.asyncio
async def test_memory_tools_execution():
    """Verify memory tools execute properly."""
    res_save = await tool_registry.execute_tool(
        "save_user_memory",
        {"fact": "User is a software engineer", "category": "work"},
        user_id="user_test_123",
    )
    assert res_save["success"] is True

    res_search = await tool_registry.execute_tool(
        "search_user_memory",
        {"query": "software engineer"},
        user_id="user_test_123",
    )
    assert res_search["success"] is True


@pytest.mark.asyncio
async def test_perplexity_tool_fallback():
    """Verify Perplexity tool returns research structure."""
    res = await tool_registry.execute_tool("perplexity_ai_research", {"prompt": "What is WebRTC?"})
    assert res["success"] is True
    assert "spoken_summary" in res
