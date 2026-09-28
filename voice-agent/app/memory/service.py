"""Memory service providing persistence, semantic retrieval, and structured extraction."""

import logging
from typing import Dict, List, Optional

from app.db.session import db_gateway
from app.memory.extractor import structured_extractor
from app.memory.models import MemoryRecord

logger = logging.getLogger(__name__)


class MemoryService:
    """Service to manage short-term and long-term user memories."""

    def __init__(self, max_cache_size: int = 1000) -> None:
        self._in_memory_store: Dict[str, List[MemoryRecord]] = {}
        self._by_id: Dict[str, MemoryRecord] = {}
        self._max_cache_size = max_cache_size

    def _prune_cache_if_needed(self) -> None:
        """Evict oldest entries when cache exceeds bounded limit."""
        if len(self._by_id) <= self._max_cache_size:
            return
        sorted_keys = sorted(
            self._by_id.keys(),
            key=lambda k: self._by_id[k].created_at,
        )
        excess = len(self._by_id) - self._max_cache_size
        for k in sorted_keys[:excess]:
            rec = self._by_id.pop(k, None)
            if rec and rec.user_id in self._in_memory_store:
                self._in_memory_store[rec.user_id] = [
                    r for r in self._in_memory_store[rec.user_id] if r.id != k
                ]

    async def save_memory(
        self,
        user_id: str,
        content: str,
        category: str = "general",
        confidence: float = 1.0,
        source: str = "conversation",
    ) -> MemoryRecord:
        """Save a memory record for a user.

        Database is authoritative when connected: if persistence fails, an exception
        is raised and the cache is not updated.
        """
        record = MemoryRecord(
            user_id=user_id,
            content=content,
            category=category,
            confidence=confidence,
            source=source,
        )

        if db_gateway.is_connected:
            try:
                query = """
                INSERT INTO memories (id, user_id, content, category, confidence, source, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """
                await db_gateway.execute_as_user(
                    user_id,
                    query,
                    record.id,
                    record.user_id,
                    record.content,
                    record.category,
                    record.confidence,
                    record.source,
                    record.created_at,
                    record.updated_at,
                )
            except Exception as exc:
                logger.exception("Failed to persist memory to Neon PostgreSQL")
                raise RuntimeError(f"Database persistence failure: {exc}") from exc

        # Cache update only commits after authoritative database write succeeds
        if user_id not in self._in_memory_store:
            self._in_memory_store[user_id] = []
        self._in_memory_store[user_id].append(record)
        self._by_id[record.id] = record
        self._prune_cache_if_needed()

        logger.info(f"Saved memory for user {user_id}: record_id={record.id}, category={category}")
        return record

    async def update_memory(
        self,
        memory_id: str,
        user_id: str,
        content: Optional[str] = None,
        category: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> Optional[MemoryRecord]:
        """Update an existing memory record by ID. Authoritative when database is connected."""
        record = self._by_id.get(memory_id)
        if not record and not db_gateway.is_connected:
            return None

        if db_gateway.is_connected:
            try:
                set_clauses = []
                params: List[object] = [memory_id]
                if content is not None:
                    params.append(content)
                    set_clauses.append(f"content = ${len(params)}")
                if category is not None:
                    params.append(category)
                    set_clauses.append(f"category = ${len(params)}")
                if confidence is not None:
                    params.append(confidence)
                    set_clauses.append(f"confidence = ${len(params)}")
                set_clauses.append("updated_at = now()")

                query = f"UPDATE memories SET {', '.join(set_clauses)} WHERE id = $1"
                status = await db_gateway.execute_as_user(user_id, query, *params)
                if status == "UPDATE 0" and not record:
                    return None
            except Exception as exc:
                logger.exception("Failed to update memory in Neon PostgreSQL")
                raise RuntimeError(f"Database update failure: {exc}") from exc

        if record:
            if content is not None:
                record.content = content
            if category is not None:
                record.category = category
            if confidence is not None:
                record.confidence = confidence
            return record

        return None

    async def delete_memory(self, memory_id: str, user_id: str) -> bool:
        """Delete a memory record by ID. Authoritative when database is connected."""
        if db_gateway.is_connected:
            try:
                await db_gateway.execute_as_user(user_id, "DELETE FROM memories WHERE id = $1", memory_id)
            except Exception as exc:
                logger.exception("Failed to delete memory from Neon PostgreSQL")
                raise RuntimeError(f"Database deletion failure: {exc}") from exc

        record = self._by_id.get(memory_id)
        if record and record.user_id != user_id:
            return False
        record = self._by_id.pop(memory_id, None)
        if record:
            user_records = self._in_memory_store.get(record.user_id, [])
            self._in_memory_store[record.user_id] = [r for r in user_records if r.id != memory_id]
            return True

        return bool(db_gateway.is_connected)

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
        """Search relevant memories for a user, hydrating from Neon PostgreSQL if connected."""
        if db_gateway.is_connected and user_id not in self._in_memory_store:
            try:
                rows = await db_gateway.fetch_as_user(
                    user_id,
                    "SELECT id, user_id, content, category, created_at FROM memories WHERE user_id = $1 ORDER BY created_at DESC LIMIT 20",
                    user_id,
                )
                if rows:
                    db_records = []
                    for d in rows:
                        data = dict(d)
                        db_record = MemoryRecord(
                            id=data["id"],
                            user_id=data["user_id"],
                            content=data["content"],
                            category=data.get("category", "general"),
                        )
                        db_records.append(db_record)
                        self._by_id[db_record.id] = db_record
                    self._in_memory_store[user_id] = db_records
            except Exception as e:
                logger.warning(f"Failed to hydrate memories from Neon PostgreSQL for {user_id}: {e}")

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
