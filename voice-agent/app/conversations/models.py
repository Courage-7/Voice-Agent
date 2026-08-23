"""Conversation models and turn records."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    """A single turn in the conversation."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    role: str  # "user" | "assistant" | "system" | "tool"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationSession(BaseModel):
    """Session recording messages and turn telemetry."""

    session_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str = "default_user"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    messages: List[ConversationMessage] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
