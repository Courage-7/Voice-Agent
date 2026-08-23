"""User domain models."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """User profile and identity record."""

    id: str = "default_user"
    full_name: str = "Default User"
    email: Optional[str] = None
    timezone: str = "UTC"
    preferred_persona: str = "executive"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)
