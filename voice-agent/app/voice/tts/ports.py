from typing import AsyncIterator, Protocol

class TextToSpeech(Protocol):
    async def synthesize(self, text_stream: AsyncIterator[str]):
        ...
