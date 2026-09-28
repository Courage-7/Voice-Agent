"""System, health, and observability endpoints."""

from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse
from app.core.config import settings
from app.db.session import db_gateway
from app.observability.metrics import metrics_collector
from app.tools.registry import tool_registry

router = APIRouter()


def _get_provider_status() -> dict[str, bool]:
    """Inspect active provider credential availability."""
    return {
        "deepgram": bool(settings.deepgram_api_key),
        "groq": bool(settings.groq_api_key),
        "neon": bool(settings.database_url and db_gateway.is_connected),
        "composio": bool(settings.composio_api_key),
    }


@router.get("/health")
async def health_check():
    """Process liveness endpoint reporting uptime, readiness breakdown, and active models."""
    providers = _get_provider_status()
    is_ready = providers["deepgram"] and providers["groq"]
    return {
        "status": "healthy",
        "readiness": "ready" if is_ready else "degraded",
        "environment": settings.environment,
        "demo_mode": settings.demo_mode,
        "tools_count": len(tool_registry.get_all_tools()),
        "groq_model": settings.groq_model,
        "deepgram_stt": settings.deepgram_stt_model,
        "deepgram_tts": settings.deepgram_tts_model,
        "turn_taking": {
            "eot_threshold": settings.deepgram_eot_threshold,
            "eot_timeout_ms": settings.deepgram_eot_timeout_ms,
        },
        "providers": providers,
    }


@router.get("/ready")
async def readiness_check(response: Response):
    """Readiness endpoint verifying critical provider credentials before traffic admission."""
    providers = _get_provider_status()
    is_ready = providers["deepgram"] and providers["groq"]
    if not is_ready:
        response.status_code = 503
        return {
            "status": "not_ready",
            "ready": False,
            "providers": providers,
            "message": "Critical provider credentials unconfigured",
        }
    return {
        "status": "ready",
        "ready": True,
        "providers": providers,
    }


@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """Prometheus exposition metrics endpoint."""
    return PlainTextResponse(metrics_collector.export_prometheus_text(), media_type="text/plain")


@router.get("/telemetry/summary")
async def telemetry_summary():
    """Structured telemetry metrics summary including latency percentiles."""
    return metrics_collector.get_summary()
