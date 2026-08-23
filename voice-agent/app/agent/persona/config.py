"""Persona configuration schema."""

from pydantic import BaseModel, Field


class PersonaConfig(BaseModel):
    """Configuration for active persona."""

    name: str = Field(default="executive", description="Name of the active persona")
    custom_instructions: str = Field(default="", description="Optional custom override instructions")
    voice_model: str = Field(default="aura-asteria-en", description="Deepgram Aura TTS voice model")
    speaking_rate: float = Field(default=1.0, description="Speech cadence rate multiplier")
