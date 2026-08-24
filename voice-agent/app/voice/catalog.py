"""Voice Catalog and TTS Model Registry for Deepgram Flux & Aura-2 Voice Models."""

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Default high-quality conversational TTS voice
DEFAULT_VOICE_MODEL = "aura-2-thalia-en"


class VoiceInfo(BaseModel):
    id: str
    name: str
    gender: str
    accent: str
    tier: str  # "flux" or "aura-2" or "aura"
    description: str


# Allowlisted Voice Models supported in Deepgram Voice Agent API
VOICE_CATALOG: List[VoiceInfo] = [
    VoiceInfo(
        id="aura-2-thalia-en",
        name="Thalia (Aura-2)",
        gender="Female",
        accent="American",
        tier="aura-2",
        description="Warm, clear, and natural conversational companion voice.",
    ),
    VoiceInfo(
        id="aura-2-orion-en",
        name="Orion (Aura-2)",
        gender="Male",
        accent="American",
        tier="aura-2",
        description="Professional, calm, and articulate assistant voice.",
    ),
    VoiceInfo(
        id="aura-2-arcas-en",
        name="Arcas (Aura-2)",
        gender="Male",
        accent="American",
        tier="aura-2",
        description="Deep, confident, and resonant voice.",
    ),
    VoiceInfo(
        id="aura-2-perseus-en",
        name="Perseus (Aura-2)",
        gender="Male",
        accent="American",
        tier="aura-2",
        description="Energetic, bright, and engaging voice.",
    ),
    VoiceInfo(
        id="aura-2-angus-en",
        name="Angus (Aura-2)",
        gender="Male",
        accent="Irish",
        tier="aura-2",
        description="Irish-accented, friendly and approachable tone.",
    ),
    VoiceInfo(
        id="aura-2-helios-en",
        name="Helios (Aura-2)",
        gender="Male",
        accent="British",
        tier="aura-2",
        description="Polished British English voice with steady cadence.",
    ),
    VoiceInfo(
        id="aura-2-zeus-en",
        name="Zeus (Aura-2)",
        gender="Male",
        accent="American",
        tier="aura-2",
        description="Authoritative and deep conversational voice.",
    ),
    VoiceInfo(
        id="aura-asteria-en",
        name="Asteria (Aura-1)",
        gender="Female",
        accent="American",
        tier="aura",
        description="Classic smooth conversational voice.",
    ),
    VoiceInfo(
        id="aura-luna-en",
        name="Luna (Aura-1)",
        gender="Female",
        accent="American",
        tier="aura",
        description="Gentle and soothing assistant voice.",
    ),
    VoiceInfo(
        id="aura-stella-en",
        name="Stella (Aura-1)",
        gender="Female",
        accent="American",
        tier="aura",
        description="Upbeat and dynamic executive voice.",
    ),
]

_ALLOWLISTED_VOICE_IDS = {v.id.lower(): v.id for v in VOICE_CATALOG}
_USER_VOICE_PREFERENCES: Dict[str, str] = {}


class VoiceCatalogService:
    """Manages allowlisted voice models and user voice preferences."""

    def get_catalog(self) -> List[Dict[str, Any]]:
        """Return the list of all supported voice models."""
        return [v.model_dump() for v in VOICE_CATALOG]

    def validate_voice(self, requested_voice: Optional[str]) -> str:
        """Validate a requested voice model ID against allowlist.

        Returns valid model string or falls back safely to DEFAULT_VOICE_MODEL.
        """
        if not requested_voice:
            return DEFAULT_VOICE_MODEL

        clean = requested_voice.strip().lower()
        if clean in _ALLOWLISTED_VOICE_IDS:
            return _ALLOWLISTED_VOICE_IDS[clean]

        # Fuzzy matching: check if requested voice matches any voice name or substring
        for v in VOICE_CATALOG:
            if clean in v.name.lower() or clean in v.id.lower():
                return v.id

        logger.warning(
            f"Requested voice '{requested_voice}' not in allowlist. Falling back to default '{DEFAULT_VOICE_MODEL}'."
        )
        return DEFAULT_VOICE_MODEL

    def get_user_voice(self, user_id: str, default: Optional[str] = None) -> str:
        """Retrieve the persisted or active voice preference for a user."""
        if user_id in _USER_VOICE_PREFERENCES:
            return _USER_VOICE_PREFERENCES[user_id]
        return self.validate_voice(default)

    def set_user_voice(self, user_id: str, voice_model: str) -> str:
        """Save a validated voice preference for a user."""
        validated = self.validate_voice(voice_model)
        _USER_VOICE_PREFERENCES[user_id] = validated
        logger.info(f"Updated voice preference for user '{user_id}' to '{validated}'.")
        return validated


voice_catalog_service = VoiceCatalogService()
