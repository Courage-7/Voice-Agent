"""User repository with Supabase and in-memory caching."""

import asyncio
from typing import Dict, Optional
from app.integrations.supabase.client import supabase_gateway
from app.users.models import UserProfile


class UserRepository:
    """Repository managing user profiles."""

    def __init__(self) -> None:
        self._cache: Dict[str, UserProfile] = {
            "default_user": UserProfile(id="default_user", full_name="User")
        }

    async def get_by_id(self, user_id: str) -> Optional[UserProfile]:
        """Fetch user by ID."""
        if user_id in self._cache:
            return self._cache[user_id]

        if supabase_gateway.is_connected:
            try:
                res = await asyncio.to_thread(
                    lambda: supabase_gateway.client.table("users")
                    .select("*").eq("id", user_id).execute()
                )
                if res.data:
                    user = UserProfile(**res.data[0])
                    self._cache[user_id] = user
                    return user
            except Exception:
                pass

        return None

    async def save(self, user: UserProfile) -> UserProfile:
        """Save or update user profile."""
        self._cache[user.id] = user
        if supabase_gateway.is_connected:
            try:
                await asyncio.to_thread(
                    lambda: supabase_gateway.client.table("users")
                    .upsert(user.model_dump()).execute()
                )
            except Exception:
                pass
        return user


user_repository = UserRepository()
