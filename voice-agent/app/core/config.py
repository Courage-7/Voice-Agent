import os
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def normalize_origin(value: str) -> str:
    """Return a canonical HTTP(S) origin or raise for an unsafe value."""
    candidate = value.strip().rstrip("/")
    parsed = urlparse(candidate)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path not in ("", "/")
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("must contain only absolute http(s) origins, separated by commas")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("contains an invalid origin port") from exc
    authority = parsed.hostname.lower()
    if port is not None:
        authority = f"{authority}:{port}"
    return f"{parsed.scheme.lower()}://{authority}"


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
    # Explicit browser origins for CORS and WebSocket handshakes. Production
    # must set this to the public HTTPS frontend origin(s); SERVER_HOST is a
    # bind address, not an origin allowlist.
    allowed_origins: str = ""

    @field_validator("clerk_authorized_parties", "allowed_origins", mode="after")
    @classmethod
    def normalize_origin_list(cls, value: str) -> str:
        if not value.strip():
            return ""
        origins = [normalize_origin(origin) for origin in value.split(",") if origin.strip()]
        if not origins:
            return ""
        return ",".join(dict.fromkeys(origins))

    @property
    def allowed_origins_list(self) -> tuple[str, ...]:
        return tuple(origin for origin in self.allowed_origins.split(",") if origin)

    @property
    def clerk_authorized_parties_list(self) -> tuple[str, ...]:
        return tuple(origin for origin in self.clerk_authorized_parties.split(",") if origin)

    # Deepgram Voice Agent & Audio Settings
    # The decoupled pipeline is the authoritative execution path: Live STT -> LangGraph Brain -> Streaming TTS.
    voice_pipeline_mode: str = "decoupled"
    deepgram_api_key: str = Field(default="", repr=False)
    deepgram_stt_model: str = "nova-3"
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

    @property
    def requires_persistent_storage(self) -> bool:
        """Whether an unavailable database must fail closed rather than use RAM."""
        return self.environment == "production"

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
        if not self.allowed_origins_list:
            raise ValueError("Set ALLOWED_ORIGINS to the public HTTPS frontend origin in production")
        if any(urlparse(origin).scheme != "https" for origin in self.allowed_origins_list):
            raise ValueError("ALLOWED_ORIGINS must use HTTPS in production")
        if not self.clerk_authorized_parties_list:
            raise ValueError("Set CLERK_AUTHORIZED_PARTIES in production")
        if not set(self.allowed_origins_list).intersection(self.clerk_authorized_parties_list):
            raise ValueError("ALLOWED_ORIGINS must overlap CLERK_AUTHORIZED_PARTIES in production")
        return self


def load_settings() -> Settings:
    # Deployment variables always take priority; tests and release images never
    # inherit local credentials from a developer's working directory.
    environment = os.environ.get("ENVIRONMENT", "development")
    if environment in ("production", "testing", "demo"):
        # pydantic-settings exposes this supported constructor argument at
        # runtime, but the inherited Pydantic type signature omits it.
        settings_factory: Any = Settings
        return settings_factory(_env_file=None)
    return Settings()


settings = load_settings()


def reload_settings() -> Settings:
    """Reload settings from disk/env and update singleton."""
    global settings
    settings = load_settings()
    return settings
