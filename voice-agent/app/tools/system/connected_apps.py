"""Tool to inspect active connected apps for the current user."""

import logging
from typing import Any, Dict
from app.integrations.composio.client import composio_gateway
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


class GetConnectedAppsTool(BaseTool):
    """Tool to retrieve currently connected apps and integrations."""

    name = "get_connected_apps"
    description = "List all apps and connectors that the user is currently connected to (e.g. Gmail, Google Calendar)."
    capability = "system"
    read_only = True
    requires_confirmation = False
    timeout_seconds = 6.0

    parameters = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        user_id = kwargs.get("user_id", "default_user")
        accounts = await composio_gateway.get_connected_accounts(entity_id=user_id)
        active_apps = [acc["app"] for acc in accounts if acc.get("status") == "ACTIVE"]

        if active_apps:
            apps_readable = ", ".join(active_apps)
            spoken = f"You are currently connected to {apps_readable}."
        else:
            spoken = "You do not have any apps connected yet. You can connect apps in the Connectors panel."

        return {
            "success": True,
            "connected_apps": active_apps,
            "count": len(active_apps),
            "spoken_summary": spoken,
        }
