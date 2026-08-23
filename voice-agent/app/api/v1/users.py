"""User profile and identity endpoints."""

from fastapi import APIRouter, HTTPException
from app.users.models import UserProfile
from app.users.schemas import UserCreateRequest, UserUpdateRequest, UserResponse
from app.users.service import user_service

router = APIRouter()


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    responses={404: {"description": "User not found."}},
)
async def get_user(user_id: str):
    """Retrieve user profile, preferred persona, and timezone."""
    user = await user_service.get_or_create_user(user_id)
    return UserResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        timezone=user.timezone,
        preferred_persona=user.preferred_persona,
    )


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    responses={404: {"description": "User not found."}},
)
async def update_user(user_id: str, payload: UserUpdateRequest):
    """Partially update user profile and persona settings."""
    existing = await user_service.repository.get_by_id(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found.")

    update_data = payload.model_dump(exclude_unset=True)
    updated_profile = existing.model_copy(update=update_data)
    saved = await user_service.repository.save(updated_profile)

    return UserResponse(
        id=saved.id,
        full_name=saved.full_name,
        email=saved.email,
        timezone=saved.timezone,
        preferred_persona=saved.preferred_persona,
    )
