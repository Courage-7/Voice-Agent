"""Tool schemas and catalog endpoint."""

from fastapi import APIRouter
from app.tools.registry import tool_registry

router = APIRouter()


@router.get("")
async def list_tools():
    """List all registered tools and their OpenAPI schemas."""
    return {
        "count": len(tool_registry.get_all_tools()),
        "tools": tool_registry.get_deepgram_function_schemas(),
    }
