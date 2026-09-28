"""Speech Payload Distiller & Token Budgeting Gateway.

Prevents LLM token exhaustion by sanitizing, pruning, and strictly budgeting
tool output payloads before they are serialized into WebSocket FunctionCallResponse
messages and added to the conversational context buffer.
"""

import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Hard budget limits for real-time voice function call returns
MAX_PAYLOAD_CHARS = 1200  # ~300-350 tokens, ideal for sub-second LLM ingestion
MAX_LIST_ITEMS = 4


class SpeechPayloadDistiller:
    """Distills raw tool outputs into compact, speech-essential facts."""

    @classmethod
    def distill(
        cls,
        tool_name: str,
        result: Dict[str, Any],
        max_chars: int = MAX_PAYLOAD_CHARS,
    ) -> str:
        """Sanitize and compress tool results into a compact JSON string under max_chars."""
        if not isinstance(result, dict):
            text = str(result)[:max_chars]
            return json.dumps({"result": text})

        # Determine success safely
        success_val = result.get("success")
        if success_val is None:
            status_val = result.get("status")
            if status_val in ("completed", "executing", "awaiting_confirmation"):
                success_val = True
            else:
                success_val = False

        distilled: Dict[str, Any] = {
            "success": bool(success_val),
        }

        # Preserve machine control handles for task resumption and policy tracking
        for k in ("task_id", "status", "action_id", "action_name"):
            if k in result and result[k] is not None:
                distilled[k] = result[k]

        # Preserve primary spoken summary and critical flags
        if "spoken_summary" in result:
            distilled["spoken_summary"] = str(result["spoken_summary"])[:300]
        if result.get("requires_confirmation"):
            distilled["requires_confirmation"] = True
            if "message" in result:
                distilled["message"] = str(result["message"])[:200]

        elif "error" in result:
            distilled["error"] = str(result["error"])[:250]

        # Domain-specific smart extraction
        elif "emails" in result and isinstance(result["emails"], list):
            distilled["count"] = result.get("count", len(result["emails"]))
            distilled["emails"] = cls._distill_emails(result["emails"][:MAX_LIST_ITEMS])

        elif "events" in result and isinstance(result["events"], list):
            distilled["count"] = len(result["events"])
            distilled["events"] = cls._distill_events(result["events"][:MAX_LIST_ITEMS])

        elif "results" in result:
            distilled["results"] = cls._distill_search_results(result["results"])

        elif "data" in result and isinstance(result["data"], dict):
            # Extract only first-level summary keys, dropping deep raw blobs
            data_dict = result["data"]
            clean_data = {}
            for k, v in data_dict.items():
                if k in ("status", "message", "count", "id", "title", "summary"):
                    clean_data[k] = v
                elif isinstance(v, (str, int, float, bool)) and len(str(v)) < 150:
                    clean_data[k] = v
            distilled["data"] = clean_data or {"status": "completed"}

        else:
            # Generic pass-through for other small tools
            for k, v in result.items():
                if k not in ("success", "spoken_summary", "task_id", "status", "action_id") and not k.startswith("_"):
                    if isinstance(v, (str, int, float, bool)):
                        distilled[k] = v
                    elif isinstance(v, (dict, list)):
                        distilled[k] = str(v)[:200]

        # Final string serialization and hard length enforcement
        serialized = json.dumps(distilled, ensure_ascii=False)
        if len(serialized) > max_chars:
            logger.info(
                f"Tool '{tool_name}' output exceeded budget ({len(serialized)} chars). Compacting to {max_chars} chars."
            )
            # Retain high-priority speech summary and control identifiers
            compact: Dict[str, Any] = {
                "success": distilled.get("success", True),
                "spoken_summary": distilled.get("spoken_summary") or f"Data retrieved from {tool_name}.",
                "truncated": True,
            }
            for k in ("task_id", "status", "action_id", "requires_confirmation"):
                if k in distilled:
                    compact[k] = distilled[k]

            # Add snippet of key items if available
            if "emails" in distilled:
                compact["emails_preview"] = [e.get("subject", "") for e in distilled["emails"][:2]]
            elif "results" in distilled:
                compact["results_preview"] = str(distilled["results"])[:300]
            serialized = json.dumps(compact, ensure_ascii=False)
            if len(serialized) > max_chars:
                serialized = serialized[:max_chars - 3] + "..."

        return serialized

    @classmethod
    def _distill_emails(cls, emails: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        clean = []
        for em in emails:
            msg_id = str(em.get("message_id") or em.get("id") or "")[:40]
            thread_id = str(em.get("thread_id") or em.get("threadId") or "")[:40]
            item: Dict[str, str] = {
                "from": str(em.get("sender") or em.get("from") or "Unknown")[:40],
                "subject": str(em.get("subject") or "No subject")[:60],
                "snippet": str(em.get("preview") or em.get("snippet") or "")[:100],
            }
            if msg_id:
                item["message_id"] = msg_id
            if thread_id:
                item["thread_id"] = thread_id
            clean.append(item)
        return clean


    @classmethod
    def _distill_events(cls, events: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        clean = []
        for ev in events:
            clean.append({
                "title": str(ev.get("title") or ev.get("summary") or "Meeting")[:50],
                "time": str(ev.get("start") or ev.get("start_time") or "")[:35],
            })
        return clean

    @classmethod
    def _distill_search_results(cls, raw: Any) -> Any:
        if isinstance(raw, str):
            return raw[:500]
        if isinstance(raw, list):
            items = []
            for item in raw[:3]:
                if isinstance(item, dict):
                    title = item.get("title") or item.get("heading") or ""
                    snippet = item.get("snippet") or item.get("text") or item.get("answer") or ""
                    items.append(f"{title}: {snippet}"[:150])
                else:
                    items.append(str(item)[:150])
            return items
        if isinstance(raw, dict):
            # Check for common search engine keys
            answer = raw.get("answer") or raw.get("snippet") or raw.get("text")
            if answer:
                return str(answer)[:500]
            organic = raw.get("organic_results") or raw.get("results")
            if isinstance(organic, list):
                return [str(o.get("snippet") or o.get("title") or "")[:120] for o in organic[:3]]
            return {k: str(v)[:100] for k, v in list(raw.items())[:3]}
        return str(raw)[:400]


speech_payload_distiller = SpeechPayloadDistiller()
