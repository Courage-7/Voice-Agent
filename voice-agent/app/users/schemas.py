"""User request and response schemas."""

from typing import Optional
from pydantic import BaseModel


class UserCreateRequest(BaseModel):
    id: str
    full_name: str
    email: Optional[str] = None
    timezone: str = "UTC"
    preferred_persona: str = "executive"


class UserUpdateRequest(BaseModel):
    """Partial update schema for PATCH. All fields optional."""
    full_name: Optional[str] = None
    email: Optional[str] = None
    timezone: Optional[str] = None
    preferred_persona: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    full_name: str
    email: Optional[str] = None
    timezone: str = "UTC"
    preferred_persona: str = "executive"
