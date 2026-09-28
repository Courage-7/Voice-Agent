"""Groq LLM Client Adapter for ultra-low latency LPU inference."""

import logging
from typing import AsyncIterator, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class GroqLLMClient:
    """Client for Groq Cloud LPU inference."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.groq_api_key
        self._client = None
        self._initialize()

    def _initialize(self) -> None:
        if settings.demo_mode:
            return
        if not self.api_key:
            logger.warning("GROQ_API_KEY is not set. Groq client running in fallback mode.")
            return

        try:
            from groq import AsyncGroq
            self._client = AsyncGroq(api_key=self.api_key)
            logger.info("Groq Async client initialized.")
        except Exception:
            logger.exception("Failed to initialize Groq client")
            self._client = None

    async def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
    ) -> AsyncIterator[str]:
        """Stream token responses from Groq LPU."""
        selected_model = model or settings.groq_model
        if not self._client:
            if settings.demo_mode:
                yield "This is a demo response. Live reasoning is disabled."
            else:
                raise RuntimeError("Groq is unavailable; no model response was generated.")
            return

        try:
            response = await self._client.chat.completions.create(
                model=selected_model,
                messages=messages,
                temperature=temperature,
                stream=True,
            )
            async for chunk in response:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    yield delta
        except Exception:
            logger.exception("Error in Groq streaming completion")
            yield " I ran into a brief hiccup while processing that."


groq_client = GroqLLMClient()
