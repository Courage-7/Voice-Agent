"""System, health, and observability endpoints."""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from app.core.config import settings
from app.observability.metrics import metrics_collector
from app.tools.registry import tool_registry

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint reporting system, models, and turn-taking configuration."""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "tools_count": len(tool_registry.get_all_tools()),
        "groq_model": settings.groq_model,
        "deepgram_stt": settings.deepgram_stt_model,
        "deepgram_tts": settings.deepgram_tts_model,
        "turn_taking": {
            "eot_threshold": settings.deepgram_eot_threshold,
            "eot_timeout_ms": settings.deepgram_eot_timeout_ms,
        },
    }


@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """Prometheus exposition metrics endpoint."""
    return PlainTextResponse(metrics_collector.export_prometheus_text(), media_type="text/plain")


@router.get("/telemetry/summary")
async def telemetry_summary():
    """Structured telemetry metrics summary including latency percentiles."""
    return metrics_collector.get_summary()
