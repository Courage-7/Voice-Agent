"""Memory data models and schemas."""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class MemoryRecord(BaseModel):
    """A persistent atomic memory record."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str = Field(default="default_user")
    content: str
    category: str = "general"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: float = 1.0
