"""Unit tests for LangGraph state graph and user service."""

import pytest
from app.agent.graph import agent_graph
from app.users.service import user_service


@pytest.mark.asyncio
async def test_user_service_profile():
    """Verify user service retrieves or creates user profile."""
    user = await user_service.get_or_create_user(user_id="user_test_42", full_name="Bob")
    assert user.id == "user_test_42"
    assert user.full_name == "Bob"
    assert user.timezone == "UTC"


@pytest.mark.asyncio
async def test_agent_graph_execution():
    """Verify LangGraph executes through load_context and reason nodes."""
    initial_state = {
        "session_id": "test_session_1",
        "user_id": "user_test_42",
        "messages": [{"role": "user", "content": "Hello, who are you?"}],
        "memory_context": "",
        "user_context": "",
        "active_tool_call": None,
        "tool_result": None,
        "response_text": "",
        "error": None,
    }

    final_state = await agent_graph.ainvoke(initial_state)

    assert "response_text" in final_state
    assert len(final_state["response_text"]) > 0
    assert final_state["user_context"] != ""
