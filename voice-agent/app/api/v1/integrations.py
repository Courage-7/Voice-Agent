"""Composio OAuth integrations and action execution router with verified user identity."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from app.auth.models import AuthUser
from app.core.dependencies import get_current_user, get_optional_user
from app.integrations.composio.client import composio_gateway
from app.tools.registry import tool_registry

router = APIRouter()


class DirectActionRequest(BaseModel):
    action_name: str
    params: Dict[str, Any]
    entity_id: str = "default_user"


@router.get("/apps")
async def get_supported_apps():
    """List all supported ecosystem apps (Gmail, Outlook, Calendar, SerpAI, Perplexity, Workspace)."""
    try:
        return {"apps": composio_gateway.get_supported_apps()}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/status")
async def get_connection_status(current_user: AuthUser = Depends(get_current_user)):
    """Get list of active connected OAuth accounts for the authenticated user."""
    # This endpoint drives the post-OAuth polling UI.  It must report the
    # provider's current state, not a pre-consent cache entry.
    accounts = await composio_gateway.get_connected_accounts(entity_id=current_user.id, force_refresh=True)
    return {"user_id": current_user.id, "connected_accounts": accounts}


@router.get(
    "/connect/{app_name}",
    responses={
        200: {"description": "OAuth authorization redirect URL generated."},
        400: {"description": "OAuth initiation failed for requested app."},
    },
)
async def initiate_oauth(
    app_name: str,
    redirect_uri: Optional[str] = Query(None, description="Optional custom post-OAuth redirect URI"),
    current_user: AuthUser = Depends(get_current_user),
):
    """Generate OAuth authorization URL bound to the authenticated user's entity ID."""
    result = await composio_gateway.initiate_connection(
        app_name=app_name,
        entity_id=current_user.id,
        redirect_uri=redirect_uri,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "OAuth initiation failed"))
    return result


@router.get("/callback", response_class=HTMLResponse)
async def oauth_callback(_status: Optional[str] = None):
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
async def disconnect_integration(
    connection_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """Revoke and disconnect an integrated account."""
    res = await composio_gateway.disconnect_account(connection_id, entity_id=current_user.id)
    if not res.get("success"):
        if res.get("status") == "authorization_error":
            raise HTTPException(status_code=403, detail=res.get("error", "Connection ownership check failed"))
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to disconnect"))
    return res


@router.get("/tools")
async def get_user_scoped_tools(current_user: AuthUser = Depends(get_current_user)):
    """Dynamically return tool schemas scoped only to the authenticated user's active capabilities."""
    accounts = await composio_gateway.get_connected_accounts(entity_id=current_user.id)
    active_caps = {"system", "memory"}

    for acc in accounts:
        if (acc.get("status") or "").upper() != "ACTIVE" and not acc.get("is_active"):
            continue
        app_name = (acc.get("app") or "").upper().replace("-", "_")
        if app_name in ["GMAIL", "OUTLOOK"]:
            active_caps.add("email")
        elif app_name in ["GOOGLECALENDAR", "OUTLOOK"]:
            active_caps.add("calendar")
        elif app_name in ["SERPAPI", "PERPLEXITYAI", "TAVILY"]:
            active_caps.add("search")
        elif app_name in [
            "GOOGLESHEETS", "GOOGLEDOCS", "GOOGLEDRIVE", "NOTION",
            "MICROSOFT_TEAMS", "WHATSAPP", "TELEGRAM", "LINKEDIN",
            "NEON", "I_LOVE_PDF"
        ]:
            active_caps.add("workspace")

    scoped_schemas = tool_registry.get_deepgram_function_schemas(capabilities=list(active_caps))
    return {
        "user_id": current_user.id,
        "active_capabilities": list(active_caps),
        "tools_count": len(scoped_schemas),
        "tools": scoped_schemas,
    }


@router.post(
    "/execute",
    responses={
        401: {"description": "Authentication required to execute actions."},
        403: {"description": "Direct write execution is restricted by policy."},
    },
)
async def execute_action(
    payload: DirectActionRequest,
    current_user: Optional[AuthUser] = Depends(get_optional_user),
):
    """Execute a Composio action with write policy enforcement and verified identity binding."""
    # 1. Reject writes through direct execution gateway
    action_upper = payload.action_name.upper()
    is_write = any(w in action_upper for w in ("SEND", "CREATE", "APPEND", "UPDATE", "DELETE", "INSERT", "BOOK", "DISPATCH"))
    if is_write:
        raise HTTPException(
            status_code=403,
            detail="Direct write execution is restricted by policy. Write operations must be confirmed through the voice agent safety gateway.",
        )

    # 2. Require authentication for read actions
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required to execute actions.",
        )

    # 3. Strictly bind entity_id to verified authenticated caller
    return await composio_gateway.execute_action(
        action_name=payload.action_name,
        params=payload.params,
        entity_id=current_user.id,
    )
