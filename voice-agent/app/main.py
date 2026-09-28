"""FastAPI Voice AI Agent Application Main Execution Entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings
from app.realtime.router import router as playground_router
from app.tools.registry import tool_registry

# Configure application logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("voice_agent")

FRONTEND_ASSETS_PATH = settings.frontend_dist_path / "assets"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup setup and graceful shutdown."""
    logger.info("Initializing Voice AI Agent...")
    from app.db.session import db_gateway
    await db_gateway.connect()

    if settings.demo_mode:
        logger.warning("DEMO MODE: external providers are disabled; local data is temporary.")
    if settings.environment == "production":
        if not (settings.frontend_dist_path / "index.html").is_file() or not FRONTEND_ASSETS_PATH.is_dir():
            raise RuntimeError("Production frontend is missing. Build the frontend and set FRONTEND_DIST_PATH.")
        from app.integrations.composio.client import composio_gateway
        from app.integrations.llm.client import groq_client
        if composio_gateway._client is None or groq_client._client is None or not db_gateway.is_connected:
            raise RuntimeError("A required production provider failed to initialize; startup refused.")
    logger.info(f"Loaded {len(tool_registry.get_all_tools())} tools into registry.")
    logger.info(f"Using Groq LLM model: {settings.groq_model}")
    logger.info(f"Using Deepgram STT/TTS: {settings.deepgram_stt_model} / {settings.deepgram_tts_model}")
    yield
    logger.info("Shutting down Voice AI Agent...")
    await db_gateway.disconnect()


app = FastAPI(
    title="Voice AI Agent API",
    description="Real-time Voice AI Agent powered by Deepgram Voice Agent API, Groq LPU, LangGraph Brain, and Composio Tools",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware for Web / UI clients
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Mount Central REST API Router (/api/...)
app.include_router(api_router)

# 2. Mount Static Assets from Frontend Build if available
if FRONTEND_ASSETS_PATH.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_ASSETS_PATH)), name="assets")

# 3. Mount Main Frontend and Playground UI (/, /playground)
app.include_router(playground_router)
