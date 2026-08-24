"""Google Workspace tools: Google Sheets, Docs, and Drive via Composio."""

from typing import Any, Dict, List, Optional
from app.integrations.composio.client import composio_gateway
from app.tools.base import BaseTool


class GoogleSheetsTool(BaseTool):
    """Tool to read from and append rows to Google Sheets."""

    name = "manage_google_sheet"
    description = "Read data from or append new rows to a Google Spreadsheet."
    capability = "workspace"
    read_only = False
    requires_confirmation = False
    timeout_seconds = 12.0

    parameters = {
        "type": "object",
        "properties": {
            "spreadsheet_id": {"type": "string", "description": "The unique ID of the Google Sheet."},
            "sheet_name": {"type": "string", "description": "The name of the worksheet/tab."},
            "action": {"type": "string", "enum": ["read", "append"], "description": "Operation to perform."},
            "values": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Row values to append when action is append.",
            },
        },
        "required": ["spreadsheet_id", "action"],
    }

    async def execute(
        self,
        spreadsheet_id: str,
        action: str,
        sheet_name: str = "Sheet1",
        values: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        user_id = kwargs.get("user_id", "default_user")
        action_name = "GOOGLESHEETS_READ" if action == "read" else "GOOGLESHEETS_APPEND"
        params = {
            "spreadsheet_id": spreadsheet_id,
            "sheet_name": sheet_name,
            "values": values or [],
        }

        res = await composio_gateway.execute_action(action_name, params, entity_id=user_id)
        if not res.get("success"):
            return {
                "success": False,
                "error": res.get("error", "Google Sheet operation failed"),
                "spoken_summary": f"I was unable to {action} data on that Google Sheet.",
            }
        return {
            "success": True,
            "spoken_summary": f"Google Sheet {action} operation completed.",
            "data": res,
        }


class GoogleDocsTool(BaseTool):
    """Tool to create or append text to Google Docs."""

    name = "manage_google_doc"
    description = "Create a new Google Doc or append text to an existing document."
    capability = "workspace"
    read_only = False
    requires_confirmation = False
    timeout_seconds = 12.0

    parameters = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Document title (when creating)."},
            "content": {"type": "string", "description": "Text content to insert or append."},
            "document_id": {"type": "string", "description": "Existing document ID (when appending)."},
        },
        "required": ["content"],
    }

    async def execute(
        self,
        content: str,
        title: Optional[str] = None,
        document_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        user_id = kwargs.get("user_id", "default_user")
        action_name = "GOOGLEDOCS_CREATE" if not document_id else "GOOGLEDOCS_APPEND"
        params = {"title": title or "New Note", "content": content, "document_id": document_id}

        res = await composio_gateway.execute_action(action_name, params, entity_id=user_id)
        if not res.get("success"):
            return {
                "success": False,
                "error": res.get("error", "Google Doc operation failed"),
                "spoken_summary": "I was unable to update that Google Doc.",
            }
        return {
            "success": True,
            "spoken_summary": "Google Doc updated successfully.",
            "data": res,
        }


class GoogleDriveTool(BaseTool):
    """Tool to search and locate files on Google Drive."""

    name = "search_google_drive"
    description = "Search for files, spreadsheets, and documents stored on Google Drive."
    capability = "workspace"
    read_only = True
    requires_confirmation = False
    timeout_seconds = 10.0

    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "File name, keywords, or search term."},
            "max_results": {"type": "integer", "description": "Maximum files to list. Defaults to 5."},
        },
        "required": ["query"],
    }

    async def execute(self, query: str, max_results: int = 5, **kwargs: Any) -> Dict[str, Any]:
        user_id = kwargs.get("user_id", "default_user")
        res = await composio_gateway.execute_action("GOOGLEDRIVE_SEARCH", {"query": query, "max_results": max_results}, entity_id=user_id)
        if not res.get("success"):
            return {
                "success": False,
                "error": res.get("error", "Google Drive search failed"),
                "spoken_summary": f"Unable to search Google Drive for '{query}'.",
            }
        return {
            "success": True,
            "spoken_summary": f"Found matching files on Google Drive for '{query}'.",
            "files": res,
        }
