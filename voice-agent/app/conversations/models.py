"""Conversation models and turn records."""

from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from pydantic import BaseModel, Field, computed_field


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

    @computed_field
    @property
    def id(self) -> str:
        return self.session_id

    @computed_field
    @property
    def title(self) -> str:
        if self.metadata and self.metadata.get("title"):
            return self.metadata["title"]
        for m in self.messages:
            if m.role == "user" and m.content:
                clean = m.content.strip()
                return clean[:45] + ("..." if len(clean) > 45 else "")
        return f"Voice Session {self.session_id[:8]}"
