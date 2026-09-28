"""Provider-verified identity models used by protected application routes."""

from typing import Optional
from pydantic import BaseModel


class AuthUser(BaseModel):
    """Identity derived from a verified Clerk session token."""
    id: str
    email: str = ""
    full_name: Optional[str] = "User"
    timezone: str = "UTC"
    preferred_persona: str = "executive"
    is_active: bool = True
