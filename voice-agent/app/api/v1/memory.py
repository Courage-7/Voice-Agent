"""Long-term memory and structured extraction endpoints."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.memory.service import memory_service

router = APIRouter()


class SaveMemoryRequest(BaseModel):
    user_id: str = "default_user"
    content: str
    category: str = "preference"


class UpdateMemoryRequest(BaseModel):
    content: Optional[str] = None
    category: Optional[str] = None


class ExtractMemoryRequest(BaseModel):
    user_id: str = "default_user"
    transcript: str


@router.get("")
async def query_memories(
    user_id: str = Query("default_user", description="User ID"),
    query: Optional[str] = Query(None, description="Search query"),
    limit: int = Query(10, description="Maximum records"),
):
    """Search or list memories and preferences for a user."""
    if query:
        results = await memory_service.search_memory(user_id=user_id, query=query, limit=limit)
    else:
        summary = await memory_service.get_user_memory_summary(user_id=user_id, limit=limit)
        results = [{"summary": summary}] if summary else []
    return {"user_id": user_id, "memories": results}


@router.post("")
async def save_memory(payload: SaveMemoryRequest):
    """Save an atomic memory or preference."""
    record = await memory_service.save_memory(
        user_id=payload.user_id,
        content=payload.content,
        category=payload.category,
    )
    return {"success": True, "memory": record.model_dump()}


@router.patch(
    "/{memory_id}",
    responses={404: {"description": "Memory record not found."}},
)
async def update_memory(memory_id: str, payload: UpdateMemoryRequest):
    """Partially update an existing memory record."""
    record = await memory_service.update_memory(
        memory_id=memory_id,
        content=payload.content,
        category=payload.category,
    )
    if not record:
        raise HTTPException(status_code=404, detail=f"Memory '{memory_id}' not found.")
    return {"success": True, "memory": record.model_dump()}


@router.delete(
    "/{memory_id}",
    responses={404: {"description": "Memory record not found."}},
)
async def delete_memory(memory_id: str):
    """Permanently delete a memory record."""
    deleted = await memory_service.delete_memory(memory_id=memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Memory '{memory_id}' not found.")
    return {"success": True, "message": f"Memory '{memory_id}' deleted."}


@router.post("/extract")
async def extract_memories(payload: ExtractMemoryRequest):
    """Extract structured facts from conversation transcripts using LangChain."""
    records = await memory_service.extract_and_save_from_transcript(
        user_id=payload.user_id,
        transcript=payload.transcript,
    )
    return {
        "success": True,
        "extracted_count": len(records),
        "memories": [r.model_dump() for r in records],
    }
