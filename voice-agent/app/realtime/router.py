"""Frontend and Playground UI serving router."""

from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

router = APIRouter()

PLAYGROUND_HTML_PATH = Path(__file__).parent / "playground.html"
FRONTEND_DIST_PATH = Path(__file__).resolve().parents[3] / "frontend" / "dist"
FRONTEND_INDEX_PATH = FRONTEND_DIST_PATH / "index.html"


@router.get("/playground", response_class=HTMLResponse, tags=["Development"])
async def voice_playground():
    """Serve the interactive Voice AI Agent playground."""
    if PLAYGROUND_HTML_PATH.exists():
        return HTMLResponse(content=PLAYGROUND_HTML_PATH.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Voice Agent Playground</h1><p>Playground HTML file not found.</p>")


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def main_frontend():
    """Serve the main React 3D frontend application if built, falling back to playground."""
    if FRONTEND_INDEX_PATH.exists():
        return HTMLResponse(content=FRONTEND_INDEX_PATH.read_text(encoding="utf-8"))
    if PLAYGROUND_HTML_PATH.exists():
        return HTMLResponse(content=PLAYGROUND_HTML_PATH.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>AETHERIS Voice AI Matrix</h1><p>Frontend assets not found.</p>")
