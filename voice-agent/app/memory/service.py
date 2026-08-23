"""Memory service providing persistence, semantic retrieval, and structured extraction."""

import asyncio
import logging
from typing import Dict, List, Optional

from app.integrations.supabase.client import supabase_gateway
from app.memory.extractor import structured_extractor
from app.memory.models import MemoryRecord

logger = logging.getLogger(__name__)


class MemoryService:
    """Service to manage short-term and long-term user memories."""

    def __init__(self) -> None:
        self._in_memory_store: Dict[str, List[MemoryRecord]] = {}
        self._by_id: Dict[str, MemoryRecord] = {}

    async def save_memory(self, user_id: str, content: str, category: str = "general") -> MemoryRecord:
        """Save a memory record for a user."""
        record = MemoryRecord(user_id=user_id, content=content, category=category)

        if user_id not in self._in_memory_store:
            self._in_memory_store[user_id] = []
        self._in_memory_store[user_id].append(record)
        self._by_id[record.id] = record

        if supabase_gateway.is_connected:
            try:
                row = {
                    "id": record.id,
                    "user_id": record.user_id,
                    "content": record.content,
                    "category": record.category,
                    "created_at": record.created_at.isoformat(),
                }
                await asyncio.to_thread(
                    lambda: supabase_gateway.client.table("memories").insert(row).execute()
                )
            except Exception:
                logger.exception("Failed to persist memory to Supabase")

        logger.info(f"Saved memory for user {user_id}: {content}")
        return record

    async def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Optional[MemoryRecord]:
        """Update an existing memory record by ID."""
        record = self._by_id.get(memory_id)
        if not record:
            return None

        if content is not None:
            record.content = content
        if category is not None:
            record.category = category

        if supabase_gateway.is_connected:
            try:
                update_data = {"content": record.content, "category": record.category}
                await asyncio.to_thread(
                    lambda: supabase_gateway.client.table("memories")
                    .update(update_data).eq("id", memory_id).execute()
                )
            except Exception:
                logger.exception("Failed to update memory in Supabase")

        return record

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory record by ID."""
        record = self._by_id.pop(memory_id, None)
        if not record:
            return False

        user_records = self._in_memory_store.get(record.user_id, [])
        self._in_memory_store[record.user_id] = [r for r in user_records if r.id != memory_id]

        if supabase_gateway.is_connected:
            try:
                await asyncio.to_thread(
                    lambda: supabase_gateway.client.table("memories")
                    .delete().eq("id", memory_id).execute()
                )
            except Exception:
                logger.exception("Failed to delete memory from Supabase")

        return True

    async def extract_and_save_from_transcript(self, user_id: str, transcript: str) -> List[MemoryRecord]:
        """Use LangChain structured output to extract and save atomic facts from a transcript."""
        extraction = await structured_extractor.extract_memories(transcript)
        saved_records = []

        for fact in extraction.facts:
            fact_text = f"{fact.subject} {fact.predicate} {fact.object_value}"
            record = await self.save_memory(user_id=user_id, content=fact_text, category=fact.category)
            saved_records.append(record)

        return saved_records

    async def search_memory(self, user_id: str, query: str, limit: int = 3) -> List[Dict[str, str]]:
        """Search relevant memories for a user."""
        records = self._in_memory_store.get(user_id, [])

        query_terms = [t for t in query.lower().split() if t]
        matches = [
            {"id": r.id, "content": r.content, "category": r.category}
            for r in records
            if not query_terms or any(t in r.content.lower() for t in query_terms)
        ]

        if not matches and records:
            matches = [{"id": r.id, "content": r.content, "category": r.category} for r in records[-limit:]]

        return matches[:limit]

    async def get_user_memory_summary(self, user_id: str, limit: int = 5) -> str:
        """Get formatted string of top recent user memories for prompt injection."""
        memories = await self.search_memory(user_id=user_id, query="", limit=limit)
        if not memories:
            return ""

        return "\n".join([f"- {m['content']} ({m.get('category', 'general')})" for m in memories])


memory_service = MemoryService()
