from typing import AsyncIterator, Protocol

class LLMProvider(Protocol):
    async def generate(self, messages, tools):
        ...

    async def stream(self, messages, tools) -> AsyncIterator[str]:
        ...
