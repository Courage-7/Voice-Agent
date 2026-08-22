from typing import AsyncIterator, Protocol

class SpeechToText(Protocol):
    async def stream(self, audio_stream: AsyncIterator[bytes]):
        ...
