"""Persona management service."""

from app.agent.persona.config import PersonaConfig
from app.agent.prompts.personas import get_persona_prompt
from app.agent.prompts.system import build_system_prompt


class PersonaService:
    """Service to resolve active personas and generate complete voice prompts."""

    def __init__(self, config: PersonaConfig | None = None):
        self.config = config or PersonaConfig()

    def get_voice_instructions(
        self,
        user_context: str = "",
        memory_context: str = "",
    ) -> str:
        """Construct full system prompt for current persona and runtime context."""
        base_persona = self.config.custom_instructions or get_persona_prompt(self.config.name)
        return build_system_prompt(
            persona_instructions=base_persona,
            user_context=user_context,
            memory_context=memory_context,
        )


persona_service = PersonaService()
