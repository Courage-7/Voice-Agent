"""Regression checks for release configuration and explicit simulation boundaries."""

from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.core.config import Settings, load_settings, settings
from app.integrations.composio.client import ComposioGateway
from app.integrations.llm.client import GroqLLMClient


def test_production_rejects_missing_configuration():
    with pytest.raises(ValidationError, match="Missing production settings"):
        Settings(
            _env_file=None,
            environment="production",
        )


def test_configuration_errors_do_not_print_credentials():
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, environment="production", groq_api_key="private-value-not-for-logs")
    assert "private-value-not-for-logs" not in str(error.value)


def test_environment_overrides_dotenv(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("GROQ_API_KEY=from-file\n", encoding="utf-8")
    monkeypatch.setenv("GROQ_API_KEY", "from-environment")
    config = Settings(_env_file=env_file)
    assert config.groq_api_key == "from-environment"
    assert "from-environment" not in repr(config)


@pytest.mark.parametrize("mode", ["testing", "production", "demo"])
def test_isolated_modes_ignore_local_dotenv(monkeypatch, mode):
    monkeypatch.setenv("ENVIRONMENT", mode)
    with patch("app.core.config.Settings") as constructor:
        load_settings()
    constructor.assert_called_once_with(_env_file=None)


def test_production_requires_clerk_verification_key():
    with pytest.raises(ValidationError, match="CLERK_JWT_KEY or CLERK_JWKS_URL"):
        Settings(
            _env_file=None, environment="production",
            deepgram_api_key="test", groq_api_key="test", composio_api_key="test",
            database_url="postgresql://user:pass@ep-xyz.neon.tech/neondb?sslmode=require",
            clerk_issuer="https://example.clerk.accounts.dev",
        )


def test_production_accepts_complete_configuration():
    config = Settings(
        _env_file=None, environment="production",
        deepgram_api_key="test", groq_api_key="test", composio_api_key="test",
        database_url="postgresql://user:pass@ep-xyz.neon.tech/neondb?sslmode=require",
        clerk_issuer="https://example.clerk.accounts.dev",
        clerk_jwks_url="https://example.clerk.accounts.dev/.well-known/jwks.json",
    )
    assert config.environment == "production"
    assert not config.demo_mode


def test_decoupled_pipeline_is_the_safe_default():
    """Default voice requests use the integration-aware execution path."""
    config = Settings(_env_file=None)
    assert config.voice_pipeline_mode == "decoupled"


async def test_unconfigured_oauth_and_disconnect_never_report_success():
    gateway = ComposioGateway(api_key="")
    connection = await gateway.initiate_connection("GMAIL", entity_id="test")
    assert connection["success"] is False
    assert "redirect_url" not in connection
    assert (await gateway.disconnect_account("missing", entity_id="test-user"))["success"] is False
    assert await gateway.get_connected_accounts("test") == []


async def test_missing_model_client_does_not_fabricate_response():
    client = GroqLLMClient(api_key="")
    with pytest.raises(RuntimeError, match="Groq is unavailable"):
        _ = [token async for token in client.stream_chat_completion([])]


async def test_demo_mode_is_explicit_and_ignores_provider_credentials(monkeypatch):
    monkeypatch.setattr(settings, "environment", "demo")
    gateway = ComposioGateway(api_key="unused-demo-key")
    client = GroqLLMClient(api_key="unused-demo-key")
    assert gateway._client is None
    assert client._client is None
    tokens = [token async for token in client.stream_chat_completion([])]
    assert "demo response" in "".join(tokens)


def test_frontend_page_and_assets_share_configured_directory():
    from app.main import FRONTEND_ASSETS_PATH
    from app.realtime.router import FRONTEND_DIST_PATH

    assert FRONTEND_DIST_PATH == settings.frontend_dist_path
    assert FRONTEND_ASSETS_PATH == FRONTEND_DIST_PATH / "assets"


async def test_production_startup_rejects_missing_frontend(monkeypatch, tmp_path):
    from app.main import app, lifespan

    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "frontend_dist_path", tmp_path / "missing")
    with pytest.raises(RuntimeError, match="Production frontend is missing"):
        async with lifespan(app):
            pass


def test_root_manifest_owns_backend_package_and_lockfile():
    import tomllib

    root = Path(__file__).resolve().parents[3]
    manifest = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))

    assert (root / "uv.lock").is_file()
    assert manifest["tool"]["setuptools"]["packages"]["find"]["where"] == ["voice-agent"]
    assert manifest["tool"]["pytest"]["ini_options"]["testpaths"] == ["voice-agent/tests"]
    assert not (root / "voice-agent" / "pyproject.toml").exists()
