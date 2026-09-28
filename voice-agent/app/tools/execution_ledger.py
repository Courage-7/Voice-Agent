"""Execution Ledger for recording and verifying executed tool actions.

Provides durable receipts, deduplication, and replay prevention for state-modifying actions.
"""

import asyncio
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional
from uuid import uuid4

from app.db.session import db_gateway

logger = logging.getLogger(__name__)


@dataclass
class ExecutionReceipt:
    """Audit receipt for an executed tool action."""

    receipt_id: str
    tool_name: str
    user_id: str
    session_id: str
    arguments_hash: str
    status: str  # "success", "failed"
    action_id: Optional[str] = None
    result_summary: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExecutionLedger:
    """Maintains an auditable log of executed actions with deduplication."""

    def __init__(self, max_cache_size: int = 500) -> None:
        self._receipts: Dict[str, ExecutionReceipt] = {}
        self._max_cache_size = max_cache_size

    def _prune_if_needed(self) -> None:
        if len(self._receipts) <= self._max_cache_size:
            return
        sorted_keys = sorted(
            self._receipts.keys(),
            key=lambda k: self._receipts[k].created_at,
        )
        excess = len(self._receipts) - self._max_cache_size
        for k in sorted_keys[:excess]:
            self._receipts.pop(k, None)

    async def record_execution(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user_id: str,
        session_id: str,
        status: str,
        action_id: Optional[str] = None,
        result_summary: str = "",
    ) -> ExecutionReceipt:
        """Record an execution receipt in memory and durable storage."""
        try:
            serialized = json.dumps(arguments, sort_keys=True, default=str)
        except Exception:
            serialized = str(sorted(arguments.items()))
        arg_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        receipt_id = f"rcpt_{uuid4().hex[:12]}"
        receipt = ExecutionReceipt(
            receipt_id=receipt_id,
            tool_name=tool_name,
            user_id=user_id,
            session_id=session_id,
            arguments_hash=arg_hash,
            status=status,
            action_id=action_id,
            result_summary=result_summary,
            created_at=time.time(),
        )
        self._receipts[receipt_id] = receipt
        self._prune_if_needed()

        if db_gateway.is_connected:
            try:
                query = """
                INSERT INTO execution_receipts (
                    id, action_id, tool_name, user_id, session_id,
                    arguments_hash, status, result_summary, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """
                await db_gateway.execute_as_user(
                    user_id,
                    query,
                    receipt.receipt_id,
                    receipt.action_id,
                    receipt.tool_name,
                    receipt.user_id,
                    receipt.session_id,
                    receipt.arguments_hash,
                    receipt.status,
                    receipt.result_summary,
                    datetime.now(timezone.utc),
                )
            except Exception as e:
                logger.warning(f"Failed to persist execution receipt {receipt_id} to Neon PostgreSQL: {e}")

        logger.info(
            f"Recorded execution receipt {receipt_id}: tool={tool_name} user={user_id} status={status}"
        )
        return receipt

    def find_recent_execution(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user_id: str,
        window_seconds: float = 60.0,
    ) -> Optional[ExecutionReceipt]:
        """Find recent successful execution with matching arguments to prevent duplicate writes."""
        try:
            serialized = json.dumps(arguments, sort_keys=True, default=str)
        except Exception:
            serialized = str(sorted(arguments.items()))
        arg_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        cutoff = time.time() - window_seconds
        for r in reversed(list(self._receipts.values())):
            if r.created_at < cutoff:
                break
            if (
                r.tool_name == tool_name
                and r.user_id == user_id
                and r.arguments_hash == arg_hash
                and r.status == "success"
            ):
                return r
        return None


execution_ledger = ExecutionLedger()
