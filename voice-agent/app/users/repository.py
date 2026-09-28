"""User repository with Neon PostgreSQL and in-memory caching."""

from typing import Dict, Optional
from app.db.session import db_gateway
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

        if db_gateway.is_connected:
            try:
                row = await db_gateway.fetchrow_as_user(user_id, "SELECT * FROM users WHERE id = $1", user_id)
                if row:
                    user = UserProfile(**dict(row))
                    self._cache[user_id] = user
                    return user
            except Exception:
                pass

        return None

    async def save(self, user: UserProfile) -> UserProfile:
        """Save or update user profile."""
        if db_gateway.is_connected:
            try:
                query = """
                INSERT INTO users (id, full_name, timezone, preferred_persona, email, metadata, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, now())
                ON CONFLICT (id) DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    timezone = EXCLUDED.timezone,
                    preferred_persona = EXCLUDED.preferred_persona,
                    email = EXCLUDED.email,
                    metadata = EXCLUDED.metadata,
                    updated_at = now()
                """
                await db_gateway.execute_as_user(
                    user.id,
                    query,
                    user.id,
                    user.full_name,
                    user.timezone,
                    user.preferred_persona,
                    user.email,
                    user.metadata,
                )
            except Exception:
                pass
        self._cache[user.id] = user
        return user


user_repository = UserRepository()
