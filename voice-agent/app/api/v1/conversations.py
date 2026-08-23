"""Conversations and call session transcript endpoints."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.conversations.service import conversation_service

router = APIRouter()


@router.get("")
async def list_conversations(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(20, description="Maximum sessions to return"),
    offset: int = Query(0, description="Offset for pagination"),
):
    """List conversation sessions with pagination."""
    sessions = conversation_service.list_sessions(
        user_id=user_id,
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
        404: {"description": "Voice session not found."},
    },
)
async def get_session_transcript(session_id: str):
    """Retrieve full transcript, turns, and metadata for a voice session."""
    session = conversation_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return session.model_dump()


@router.delete(
    "/{session_id}",
    responses={
        200: {"description": "Session deleted successfully."},
        404: {"description": "Voice session not found."},
    },
)
async def delete_conversation(session_id: str):
    """Delete a conversation session and all its messages."""
    deleted = await conversation_service.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return {"success": True, "message": f"Session '{session_id}' deleted."}
