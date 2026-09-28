"""Conversations and call session transcript endpoints with authenticated tenant isolation."""

from fastapi import APIRouter, Depends, HTTPException, Query
from app.auth.models import AuthUser
from app.conversations.service import conversation_service
from app.core.dependencies import get_current_user

router = APIRouter()


@router.get("")
async def list_conversations(
    current_user: AuthUser = Depends(get_current_user),
    limit: int = Query(20, description="Maximum sessions to return"),
    offset: int = Query(0, description="Offset for pagination"),
):
    """List conversation sessions for authenticated user with pagination."""
    sessions = await conversation_service.list_sessions_async(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )
    return {
        "count": len(sessions),
        "limit": limit,
        "offset": offset,
        "conversations": [s.model_dump() for s in sessions],
    }


@router.get(
    "/{session_id}",
    responses={
        200: {"description": "Session transcript retrieved successfully."},
        403: {"description": "Access denied: session belongs to another user."},
        404: {"description": "Voice session not found."},
    },
)
async def get_session_transcript(
    session_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """Retrieve full transcript, turns, and metadata for an owned voice session."""
    session = await conversation_service.get_session_async(session_id, user_id=current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied: you do not own this conversation.")
    return session.model_dump()


@router.delete(
    "/{session_id}",
    responses={
        200: {"description": "Session deleted successfully."},
        403: {"description": "Access denied: session belongs to another user."},
        404: {"description": "Voice session not found."},
        503: {"description": "Database unavailable."},
    },
)
async def delete_conversation(
    session_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """Delete a conversation session and all its messages if owned by the caller."""
    session = conversation_service.get_session(session_id)
    if session and session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied: you do not own this conversation.")
    try:
        deleted = await conversation_service.delete_session(session_id, user_id=current_user.id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return {"success": True, "message": f"Session '{session_id}' deleted."}
