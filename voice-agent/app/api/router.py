"""Central API router aggregating all versioned REST endpoints."""

from fastapi import APIRouter
from app.api.v1.conversations import router as conversations_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.memory import router as memory_router
from app.api.v1.system import router as system_router
from app.api.v1.tools import router as tools_router
from app.api.v1.users import router as users_router
from app.api.v1.voice import router as voice_router

api_router = APIRouter(prefix="/api")

# Register all sub-routers
api_router.include_router(system_router, tags=["System"])
api_router.include_router(voice_router, prefix="/voice", tags=["Voice"])
api_router.include_router(integrations_router, prefix="/integrations", tags=["Integrations"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(memory_router, prefix="/memories", tags=["Memory"])
api_router.include_router(conversations_router, prefix="/conversations", tags=["Conversations"])
api_router.include_router(tools_router, prefix="/tools", tags=["Tools"])
