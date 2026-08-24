"""Unit tests for Phase 3: Composio Sessions Migration."""

import asyncio
from unittest.mock import MagicMock, patch
import pytest

from app.integrations.composio.client import ComposioGateway


@pytest.mark.asyncio
async def test_get_or_create_user_session_caching():
    """Verify ComposioGateway creates and caches user-scoped sessions."""
    gateway = ComposioGateway(api_key="mock_key")
    mock_client = MagicMock()
    mock_session = MagicMock()
    mock_client.sessions.create.return_value = mock_session
    gateway._client = mock_client

    # First call -> creates session
    session1 = await gateway.get_or_create_user_session(user_id="user_alice")
    assert session1 == mock_session
    assert mock_client.sessions.create.called
    assert mock_client.sessions.create.call_args.kwargs["user_id"] == "user_alice"

    # Second call -> returns cached session without creating another
    mock_client.sessions.create.reset_mock()
    session2 = await gateway.get_or_create_user_session(user_id="user_alice")
    assert session2 == mock_session
    assert not mock_client.sessions.create.called


@pytest.mark.asyncio
async def test_discover_user_tools():
    """Verify discover_user_tools inspects session tools dynamically."""
    gateway = ComposioGateway(api_key="mock_key")
    mock_client = MagicMock()
    mock_session = MagicMock()
    mock_tool = MagicMock()
    mock_tool.slug = "CUSTOM_WORKFLOW_TOOL"
    mock_tool.description = "Runs a custom workflow."
    mock_tool.parameters = {"type": "object"}
    mock_session.tools.return_value = [mock_tool]

    mock_client.sessions.create.return_value = mock_session
    gateway._client = mock_client

    discovered = await gateway.discover_user_tools("user_bob")
    assert len(discovered) == 1
    assert discovered[0]["slug"] == "CUSTOM_WORKFLOW_TOOL"
    assert discovered[0]["description"] == "Runs a custom workflow."


@pytest.mark.asyncio
async def test_composio_fallback_mode_when_unconfigured():
    """Verify ComposioGateway gracefully handles unconfigured client."""
    gateway = ComposioGateway(api_key="mock")
    gateway._client = None

    session = await gateway.get_or_create_user_session("user_fallback")
    assert session is None

    discovered = await gateway.discover_user_tools("user_fallback")
    assert discovered == []
