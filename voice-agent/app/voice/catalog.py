"""Voice Catalog and TTS Model Registry for Deepgram Flux & Aura-2 Voice Models."""

import asyncio
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

    async def get_user_voice_async(self, user_id: str, default: Optional[str] = None) -> str:
        """Retrieve voice preference from Neon user profile metadata, falling back to cache or default."""
        if user_id in _USER_VOICE_PREFERENCES:
            return _USER_VOICE_PREFERENCES[user_id]

        from app.core.config import settings
        from app.db.session import db_gateway

        if db_gateway.is_connected:
            try:
                from app.users.repository import user_repository
                user = await user_repository.get_by_id(user_id)
                if user and user.metadata and "voice_model" in user.metadata:
                    validated = self.validate_voice(user.metadata["voice_model"])
                    _USER_VOICE_PREFERENCES[user_id] = validated
                    return validated
            except Exception as e:
                logger.warning(f"Failed to fetch voice preference for user {user_id} from DB: {e}")
                if settings.requires_persistent_storage:
                    raise RuntimeError("Persistent voice preference lookup failed.") from e

        if settings.requires_persistent_storage and not db_gateway.is_connected:
            raise RuntimeError("Persistent storage is unavailable; refusing to use in-memory voice preference.")

        return self.validate_voice(default)

    def get_user_voice(self, user_id: str, default: Optional[str] = None) -> str:
        """Retrieve the persisted or active voice preference for a user."""
        if user_id in _USER_VOICE_PREFERENCES:
            return _USER_VOICE_PREFERENCES[user_id]
        return self.validate_voice(default)

    async def set_user_voice_async(self, user_id: str, voice_model: str) -> str:
        """Save a validated voice preference to Neon user profile metadata."""
        validated = self.validate_voice(voice_model)
        _USER_VOICE_PREFERENCES[user_id] = validated

        from app.core.config import settings
        from app.db.session import db_gateway

        if db_gateway.is_connected:
            try:
                from app.users.repository import user_repository
                user = await user_repository.get_by_id(user_id)
                if user:
                    user.metadata["voice_model"] = validated
                    await user_repository.save(user)
                else:
                    from app.users.models import UserProfile
                    new_user = UserProfile(id=user_id, metadata={"voice_model": validated})
                    await user_repository.save(new_user)
                logger.info(f"Persisted voice preference for user '{user_id}' to '{validated}' in Neon.")
            except Exception as e:
                logger.warning(f"Failed to persist voice preference for user {user_id} to DB: {e}")
                if settings.requires_persistent_storage:
                    raise RuntimeError("Failed to persist voice preference to database.") from e
        elif settings.requires_persistent_storage:
            raise RuntimeError("Persistent storage is unavailable; refusing to store voice preference in-memory.")

        return validated

    def set_user_voice(self, user_id: str, voice_model: str) -> str:
        """Save a validated voice preference for a user in memory."""
        validated = self.validate_voice(voice_model)
        _USER_VOICE_PREFERENCES[user_id] = validated
        logger.info(f"Updated voice preference for user '{user_id}' to '{validated}'.")
        return validated


voice_catalog_service = VoiceCatalogService()
