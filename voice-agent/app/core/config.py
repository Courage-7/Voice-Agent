from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global Application and Vendor Settings."""

    model_config = SettingsConfigDict(
        env_file=(".env", "voice-agent/.env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server Configuration
    environment: str = "development"
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    log_level: str = "INFO"

    # Deepgram Voice Agent & Audio Settings
    deepgram_api_key: str = ""
    deepgram_agent_ws_url: str = "wss://agent.deepgram.com/v1/agent/converse"
    deepgram_stt_model: str = "nova-2"
    deepgram_tts_model: str = "aura-asteria-en"
    input_sample_rate: int = 16000
    output_sample_rate: int = 24000

    # Groq LLM Inference (Ultra-low latency LPU)
    groq_api_key: str = ""
    groq_model: str = "groq/compound"
    groq_fast_model: str = "groq/compound-mini"
    groq_temperature: float = 0.3
    groq_max_tokens: int = 1024

    # Composio Integration Gateway (OAuth for Gmail, Outlook, Calendar, SerpAI, Perplexity, Workspace)
    composio_api_key: str = ""

    # Supabase Long-Term Memory & Conversation Store
    supabase_url: str = ""
    supabase_key: str = ""


settings = Settings()
