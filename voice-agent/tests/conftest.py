"""Credential-free, offline test configuration loaded before application imports."""

import asyncio
import os
import socket
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

# Never allow the developer's .env or inherited vendor credentials into tests.
os.environ["ENVIRONMENT"] = "testing"
for name in ("DEEPGRAM_API_KEY", "GROQ_API_KEY", "COMPOSIO_API_KEY", "DATABASE_URL", "NEON_DATABASE_URL"):
    os.environ[name] = ""

_original_connect = socket.socket.connect
_original_connect_ex = socket.socket.connect_ex
_blocked_connections: list[str] = []


def _check_address(address):
    # Windows asyncio uses loopback sockets internally; TestClient itself uses ASGI.
    if isinstance(address, tuple) and address[0] not in ("127.0.0.1", "::1", "localhost"):
        _blocked_connections.append(str(address[0]))
        raise AssertionError("Unexpected external network access: inject a fake provider")


def _offline_connect(sock, address):
    _check_address(address)
    return _original_connect(sock, address)


def _offline_connect_ex(sock, address):
    _check_address(address)
    return _original_connect_ex(sock, address)


# Install during collection too, before any module-level client can connect.
socket.socket.connect = _offline_connect
socket.socket.connect_ex = _offline_connect_ex


def pytest_unconfigure(config):
    socket.socket.connect = _original_connect
    socket.socket.connect_ex = _original_connect_ex


@pytest.fixture(autouse=True)
def isolated_application_state(monkeypatch):
    from app.agent.complex_tasks.engine import complex_task_engine
    from app.api.v1 import voice
    from app.conversations.service import conversation_service
    from app.integrations.composio.client import composio_gateway
    from app.integrations.llm.client import groq_client
    from app.db.session import db_gateway
    from app.memory.service import memory_service
    from app.observability.metrics import metrics_collector
    from app.tools.execution_ledger import execution_ledger
    from app.tools.pending_actions import pending_action_store
    from app.users.repository import user_repository
    from app.voice import catalog

    for obj, attr in (
        (complex_task_engine, "_active_tasks"),
        (conversation_service, "_sessions"), (memory_service, "_in_memory_store"),
        (memory_service, "_by_id"), (user_repository, "_cache"),
        (pending_action_store, "_actions"), (execution_ledger, "_receipts"),
        (composio_gateway, "_user_sessions"), (composio_gateway, "_auth_configs_cache"),
        (voice, "_active_sessions"), (catalog, "_USER_VOICE_PREFERENCES"),
    ):
        monkeypatch.setattr(obj, attr, {})
    monkeypatch.setattr(db_gateway, "_pool", None)
    monkeypatch.setattr(db_gateway, "_is_available", False)
    monkeypatch.setattr(composio_gateway, "_client", None)
    monkeypatch.setattr(groq_client, "_client", None)
    for name, value in vars(type(metrics_collector)()).items():
        monkeypatch.setattr(metrics_collector, name, value)
    yield
    # A provider may catch the connection exception. That must still fail the test.
    if _blocked_connections:
        attempts = len(_blocked_connections)
        _blocked_connections.clear()
        pytest.fail(f"{attempts} unexpected external connection(s) attempted; use an explicit fake")


@pytest.fixture
def fake_composio(monkeypatch):
    """SDK-shaped account fixture for tests that explicitly exercise connection flows."""
    from app.integrations.composio.client import composio_gateway

    account = SimpleNamespace(id="conn_test_gmail", status="ACTIVE", toolkit=SimpleNamespace(slug="gmail"))
    client = SimpleNamespace(
        auth_configs=SimpleNamespace(list=Mock(return_value=SimpleNamespace(items=[
            SimpleNamespace(id="auth_test_gmail", toolkit=SimpleNamespace(slug="gmail")),
        ]))),
        connected_accounts=SimpleNamespace(
            link=Mock(return_value=SimpleNamespace(
                redirect_url="https://oauth.example.invalid/test-gmail", connected_account_id=account.id,
            )),
            list=Mock(return_value=SimpleNamespace(items=[account])),
            delete=Mock(),
        ),
    )
    monkeypatch.setattr(composio_gateway, "_client", client)
    return client


@pytest.fixture
def fake_voice_provider(monkeypatch):
    from app.integrations.deepgram.agent_session import DeepgramVoiceAgentSession
    from app.realtime.orchestrator import DualStreamVoiceOrchestrator

    methods = {
        "connect": AsyncMock(return_value=True), "close": AsyncMock(),
        "send_audio": AsyncMock(), "inject_user_message": AsyncMock(),
    }
    for name, method in methods.items():
        monkeypatch.setattr(DeepgramVoiceAgentSession, name, method)
        monkeypatch.setattr(DualStreamVoiceOrchestrator, name, method)
    return SimpleNamespace(**methods)


@pytest.fixture
def fake_reasoning(monkeypatch):
    from app.integrations.llm.client import groq_client

    async def completion(**kwargs):
        yield "A deterministic test response."

    monkeypatch.setattr(groq_client, "stream_chat_completion", completion)
