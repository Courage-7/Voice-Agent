"""User profile and identity endpoints with tenant isolation."""

from fastapi import APIRouter, Depends, HTTPException
from app.auth.models import AuthUser
from app.core.dependencies import get_current_user
from app.users.schemas import UserResponse, UserUpdateRequest
from app.users.service import user_service

router = APIRouter()


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    responses={
        403: {"description": "Access denied: cannot view another user's profile."},
        404: {"description": "User not found."},
    },
)
async def get_user(
    user_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """Retrieve authenticated user's own profile, preferred persona, and timezone."""
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied: cannot view another user's profile.")

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
    responses={
        403: {"description": "Access denied: cannot update another user's profile."},
        404: {"description": "User not found."},
    },
)
async def update_user(
    user_id: str,
    payload: UserUpdateRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """Partially update authenticated user's own profile and persona settings."""
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied: cannot update another user's profile.")

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
