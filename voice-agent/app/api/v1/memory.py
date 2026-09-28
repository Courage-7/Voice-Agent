"""Long-term memory and structured extraction endpoints with verified user isolation."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from app.auth.models import AuthUser
from app.core.dependencies import get_current_user
from app.memory.service import memory_service

router = APIRouter()


class SaveMemoryRequest(BaseModel):
    content: str
    category: str = "preference"


class UpdateMemoryRequest(BaseModel):
    content: Optional[str] = None
    category: Optional[str] = None


class ExtractMemoryRequest(BaseModel):
    transcript: str


@router.get("")
async def query_memories(
    current_user: AuthUser = Depends(get_current_user),
    query: Optional[str] = Query(None, description="Search query"),
    limit: int = Query(10, description="Maximum records"),
):
    """Search or list memories and preferences for the authenticated user."""
    if query:
        results = await memory_service.search_memory(user_id=current_user.id, query=query, limit=limit)
    else:
        summary = await memory_service.get_user_memory_summary(user_id=current_user.id, limit=limit)
        results = [{"summary": summary}] if summary else []
    return {"user_id": current_user.id, "memories": results}


@router.post("", responses={503: {"description": "Database unavailable."}})
async def save_memory(
    payload: SaveMemoryRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """Save an atomic memory or preference for the authenticated user."""
    try:
        record = await memory_service.save_memory(
            user_id=current_user.id,
            content=payload.content,
            category=payload.category,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"success": True, "memory": record.model_dump()}


@router.patch(
    "/{memory_id}",
    responses={404: {"description": "Memory record not found."}, 503: {"description": "Database unavailable."}},
)
async def update_memory(
    memory_id: str,
    payload: UpdateMemoryRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """Partially update an existing memory record."""
    try:
        record = await memory_service.update_memory(
            memory_id=memory_id,
            user_id=current_user.id,
            content=payload.content,
            category=payload.category,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    if not record:
        raise HTTPException(status_code=404, detail=f"Memory '{memory_id}' not found.")
    return {"success": True, "memory": record.model_dump()}


@router.delete(
    "/{memory_id}",
    responses={404: {"description": "Memory record not found."}, 503: {"description": "Database unavailable."}},
)
async def delete_memory(
    memory_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """Permanently delete a memory record."""
    try:
        deleted = await memory_service.delete_memory(memory_id=memory_id, user_id=current_user.id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Memory '{memory_id}' not found.")
    return {"success": True, "message": f"Memory '{memory_id}' deleted."}


@router.post("/extract")
async def extract_memories(
    payload: ExtractMemoryRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """Extract structured facts from conversation transcripts using LLM."""
    records = await memory_service.extract_and_save_from_transcript(
        user_id=current_user.id,
        transcript=payload.transcript,
    )
    return {
        "success": True,
        "extracted_count": len(records),
        "memories": [r.model_dump() for r in records],
    }
