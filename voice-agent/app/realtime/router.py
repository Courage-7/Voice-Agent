"""Playground UI serving router."""

from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

PLAYGROUND_HTML_PATH = Path(__file__).parent / "playground.html"


@router.get("/playground", response_class=HTMLResponse, tags=["Development"])
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def voice_playground():
    """Serve the interactive Voice AI Agent testing playground."""
    if PLAYGROUND_HTML_PATH.exists():
        return HTMLResponse(content=PLAYGROUND_HTML_PATH.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Voice Agent Playground</h1><p>Playground HTML file not found.</p>")
