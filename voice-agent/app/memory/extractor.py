"""Structured memory extraction using LangChain and Groq."""

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)


class ExtractedMemoryFact(BaseModel):
    """Atomic fact extracted from conversation."""

    subject: str = Field(description="Entity or subject of the memory (e.g. 'user', 'project', 'colleague').")
    predicate: str = Field(description="Relationship or attribute (e.g. 'prefers_meeting_time', 'works_on').")
    object_value: str = Field(description="The concrete fact, value, or preference.")
    category: str = Field(
        default="preference",
        description="Category: 'preference', 'work', 'routine', 'personal', or 'general'.",
    )
    confidence: float = Field(default=0.9, description="Extraction confidence score between 0.0 and 1.0.")


class ConversationMemoryExtraction(BaseModel):
    """Complete structured extraction schema for conversation turns."""

    facts: List[ExtractedMemoryFact] = Field(default_factory=list, description="List of atomic facts extracted.")
    topics_discussed: List[str] = Field(default_factory=list, description="Key topics discussed in the turn.")
    overall_summary: str = Field(default="", description="1-sentence conversational summary.")


class StructuredMemoryExtractor:
    """Extracts structured memories from conversational transcripts using LangChain and Groq."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.groq_api_key

    async def extract_memories(self, transcript: str) -> ConversationMemoryExtraction:
        """Extract structured facts using ChatGroq.with_structured_output()."""
        if not transcript.strip():
            return ConversationMemoryExtraction()

        # Try LangChain ChatGroq with structured output
        try:
            from langchain_groq import ChatGroq

            llm = ChatGroq(
                api_key=self.api_key,
                model_name=settings.groq_fast_model,  # Use fast 8B model for extraction
                temperature=0.1,
            )
            structured_llm = llm.with_structured_output(ConversationMemoryExtraction)

            prompt = (
                "Extract all lasting personal facts, user preferences, and important details from this conversation turn. "
                "Only extract meaningful, long-term context:\n\n"
                f"{transcript}"
            )

            result = await structured_llm.ainvoke(prompt)
            if isinstance(result, ConversationMemoryExtraction):
                logger.info(f"Extracted {len(result.facts)} structured facts from transcript.")
                return result

        except Exception as e:
            logger.debug(f"LangChain structured output fallback: {e}")

        # Resilient heuristic fallback
        return ConversationMemoryExtraction(
            overall_summary=transcript[:120],
            topics_discussed=["conversation"],
        )


structured_extractor = StructuredMemoryExtractor()
