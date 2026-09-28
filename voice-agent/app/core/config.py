import os
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Global Application and Vendor Settings."""

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / "voice-agent" / ".env", PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    # Server Configuration
    environment: Literal["development", "testing", "demo", "production"] = "development"
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    log_level: str = "INFO"
    frontend_dist_path: Path = PROJECT_ROOT / "frontend" / "dist"
    # Clerk owns browser authentication. A PEM key avoids a network request on
    # every FastAPI token verification; JWKS is the supported fallback.
    clerk_issuer: str = ""
    clerk_jwt_key: str = Field(default="", repr=False)
    clerk_jwks_url: str = ""
    clerk_authorized_parties: str = "http://localhost:5173,http://localhost:8000"

    # Deepgram Voice Agent & Audio Settings
    # The decoupled pipeline is the canonical execution path: it resolves a
    # connected account before executing an integration action.  The legacy
    # Deepgram-managed function loop remains an explicit compatibility mode,
    # but must not be the default because it can stop after capability lookup.
    voice_pipeline_mode: Literal["decoupled", "deepgram_agent"] = "decoupled"
    deepgram_api_key: str = Field(default="", repr=False)
    deepgram_agent_ws_url: str = "wss://agent.deepgram.com/v1/agent/converse"
    deepgram_stt_model: str = "nova-2"
    deepgram_tts_model: str = "aura-2-thalia-en"
    input_sample_rate: int = 16000
    output_sample_rate: int = 24000

    # Advanced Turn-Taking & Endpointing
    deepgram_eot_threshold: float = 0.75
    deepgram_eot_timeout_ms: int = 500

    # Groq LLM Inference (Ultra-low latency LPU)
    groq_api_key: str = Field(default="", repr=False)
    groq_model: str = "openai/gpt-oss-20b"
    groq_fast_model: str = "openai/gpt-oss-20b"
    groq_temperature: float = 0.3
    groq_max_tokens: int = 1024

    @field_validator("groq_model", "groq_fast_model", mode="after")
    @classmethod
    def sanitize_groq_model(cls, v: str) -> str:
        if not v or "llama" in v.lower():
            return "openai/gpt-oss-20b"
        return v

    # Composio Integration Gateway (OAuth for Gmail, Outlook, Calendar, SerpAI, Perplexity, Workspace)
    composio_api_key: str = Field(default="", repr=False)

    # Neon Serverless PostgreSQL Database
    database_url: str = Field(default="", repr=False)

    @model_validator(mode="before")
    @classmethod
    def resolve_database_url(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("database_url") and data.get("neon_database_url"):
                data["database_url"] = data["neon_database_url"]
        return data

    @property
    def demo_mode(self) -> bool:
        return self.environment == "demo"

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        if self.environment != "production":
            return self
        required = (
            "deepgram_api_key", "groq_api_key", "composio_api_key",
            "database_url", "clerk_issuer",
        )
        missing = [name.upper() for name in required if not getattr(self, name).strip()]
        if missing:
            raise ValueError("Missing production settings: " + ", ".join(missing))
        if not self.database_url.startswith(("postgresql://", "postgres://")):
            raise ValueError("Production DATABASE_URL must start with postgresql:// or postgres://")
        if not (self.clerk_jwt_key.strip() or self.clerk_jwks_url.strip()):
            raise ValueError("Set CLERK_JWT_KEY or CLERK_JWKS_URL in production")
        return self


def load_settings() -> Settings:
    # Deployment variables always take priority; tests and release images never
    # inherit local credentials from a developer's working directory.
    environment = os.environ.get("ENVIRONMENT", "development")
    if environment in ("production", "testing", "demo"):
        return Settings(_env_file=None)
    return Settings()


settings = load_settings()


def reload_settings() -> Settings:
    """Reload settings from disk/env and update singleton."""
    global settings
    settings = load_settings()
    return settings
