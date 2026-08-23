"""User business logic service."""

from typing import Optional
from app.users.models import UserProfile
from app.users.repository import user_repository


class UserService:
    """Service to handle user context and profiles."""

    def __init__(self) -> None:
        self.repository = user_repository

    async def get_or_create_user(self, user_id: str, full_name: str = "User") -> UserProfile:
        """Get existing user or initialize profile."""
        user = await self.repository.get_by_id(user_id)
        if not user:
            user = UserProfile(id=user_id, full_name=full_name)
            await self.repository.save(user)
        return user


user_service = UserService()
