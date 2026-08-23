"""FastAPI Voice AI Agent Application Main Execution Entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup setup and graceful shutdown."""
    logger.info("Initializing Voice AI Agent...")
    logger.info(f"Loaded {len(tool_registry.get_all_tools())} tools into registry.")
    logger.info(f"Using Groq LLM model: {settings.groq_model}")
    logger.info(f"Using Deepgram STT/TTS: {settings.deepgram_stt_model} / {settings.deepgram_tts_model}")
    yield
    logger.info("Shutting down Voice AI Agent...")


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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Mount Central REST API Router (/api/...)
app.include_router(api_router)

# 2. Mount Playground UI (/, /playground)
app.include_router(playground_router)
