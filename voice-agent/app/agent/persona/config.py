"""Persona configuration schema."""

from pydantic import BaseModel, Field


class PersonaConfig(BaseModel):
    """Configuration for active persona."""

    name: str = Field(default="companion", description="Name of the active persona")
    custom_instructions: str = Field(default="", description="Optional custom override instructions")
    voice_model: str = Field(default="aura-2-thalia-en", description="Deepgram Flux / Aura-2 TTS voice model")
    speaking_rate: float = Field(default=1.0, description="Speech cadence rate multiplier")
