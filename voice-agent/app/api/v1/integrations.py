"""Composio OAuth integrations and action execution router."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from app.integrations.composio.client import composio_gateway
from app.tools.registry import tool_registry

router = APIRouter()
USER_ENTITY_DESC = "User or Entity ID"


class DirectActionRequest(BaseModel):
    action_name: str
    params: Dict[str, Any]
    entity_id: str = "default_user"


@router.get("/apps")
async def get_supported_apps():
    """List all supported ecosystem apps (Gmail, Outlook, Calendar, SerpAI, Perplexity, Workspace)."""
    return {"apps": composio_gateway.get_supported_apps()}


@router.get("/status")
async def get_connection_status(user_id: str = Query("default_user", description=USER_ENTITY_DESC)):
    """Get list of active connected OAuth accounts for the user."""
    accounts = await composio_gateway.get_connected_accounts(entity_id=user_id)
    return {"user_id": user_id, "connected_accounts": accounts}


@router.get(
    "/connect/{app_name}",
    responses={
        200: {"description": "OAuth authorization redirect URL generated."},
        400: {"description": "OAuth initiation failed for requested app."},
    },
)
async def initiate_oauth(
    app_name: str,
    user_id: str = Query("default_user", description=USER_ENTITY_DESC),
    redirect_uri: Optional[str] = Query(None, description="Optional custom post-OAuth redirect URI"),
):
    """Generate OAuth authorization URL to connect an external app."""
    result = await composio_gateway.initiate_connection(
        app_name=app_name,
        entity_id=user_id,
        redirect_uri=redirect_uri,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "OAuth initiation failed"))
    return result


@router.get("/callback", response_class=HTMLResponse)
async def oauth_callback(status: Optional[str] = None):
    """OAuth callback page shown after completing OAuth consent in popup."""
    return HTMLResponse(content="""
    <html>
        <head><title>OAuth Connected</title></head>
        <body style="background:#0b0f19;color:#fff;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;">
            <div style="text-align:center;padding:24px;border:1px solid #232f48;border-radius:12px;background:#151d2f;">
                <h2 style="color:#10b981;">Account Connected Successfully</h2>
                <p style="color:#94a3b8;margin-top:8px;">You can now close this window and return to the Voice Playground.</p>
                <script>setTimeout(() => { if (window.opener) window.close(); }, 2000);</script>
            </div>
        </body>
    </html>
    """)


@router.delete(
    "/{connection_id}",
    responses={
        200: {"description": "Connection successfully disconnected."},
        400: {"description": "Failed to disconnect connection."},
    },
)
async def disconnect_integration(connection_id: str):
    """Revoke and disconnect an integrated account."""
    res = await composio_gateway.disconnect_account(connection_id)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to disconnect"))
    return res


@router.get("/tools")
async def get_user_scoped_tools(user_id: str = Query("default_user", description=USER_ENTITY_DESC)):
    """Dynamically return tool schemas scoped only to the user's active connected capabilities."""
    accounts = await composio_gateway.get_connected_accounts(entity_id=user_id)
    active_caps = {"system", "memory"}

    for acc in accounts:
        app_name = (acc.get("app") or "").upper()
        if app_name in ["GMAIL", "OUTLOOK"]:
            active_caps.add("email")
        elif app_name in ["GOOGLECALENDAR", "OUTLOOK"]:
            active_caps.add("calendar")
        elif app_name in ["SERPAPI", "PERPLEXITYAI"]:
            active_caps.add("search")
        elif app_name in ["GOOGLESHEETS", "GOOGLEDOCS", "GOOGLEDRIVE"]:
            active_caps.add("workspace")

    scoped_schemas = tool_registry.get_deepgram_function_schemas(capabilities=list(active_caps))
    return {
        "user_id": user_id,
        "active_capabilities": list(active_caps),
        "tools_count": len(scoped_schemas),
        "tools": scoped_schemas,
    }


@router.post("/execute")
async def execute_action(payload: DirectActionRequest):
    """Directly test-execute a Composio action for a connected user entity."""
    return await composio_gateway.execute_action(
        action_name=payload.action_name,
        params=payload.params,
        entity_id=payload.entity_id,
    )
