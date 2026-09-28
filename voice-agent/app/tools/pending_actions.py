"""Pending Action Ledger & Write Authorization Gateway.

Provides a trusted server-side store for proposed actions requiring user confirmation.
Binds approval to exact validated arguments, user, session, and one-time execution.
Prevents model hallucinations, argument manipulation, replayed confirmations, and cross-user execution.
"""

import hashlib
import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_EXPIRY_SECONDS = 300.0  # 5 minutes default confirmation window


def compute_arguments_hash(arguments: Dict[str, Any]) -> str:
    """Compute deterministic SHA256 hash of normalized arguments dictionary."""
    try:
        serialized = json.dumps(arguments, sort_keys=True, ensure_ascii=False)
    except Exception:
        serialized = str(sorted(arguments.items()))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@dataclass
class PendingAction:
    """Immutable record of an action awaiting explicit user approval."""

    action_id: str
    tool_name: str
    arguments: Dict[str, Any]
    arguments_hash: str
    user_id: str
    session_id: str
    proposal_summary: str
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + DEFAULT_EXPIRY_SECONDS)
    consumed: bool = False
    consumed_at: Optional[float] = None
    state: str = "pending"  # pending, approved, rejected, expired, executed

    def is_expired(self) -> bool:
        """Check if action confirmation window has elapsed."""
        return time.time() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert pending action to serializable dictionary."""
        return asdict(self)


from datetime import datetime, timezone
from app.db.session import db_gateway

class PendingActionStore:
    """Durable repository interface for pending actions (DB-backed when Neon PostgreSQL is connected)."""

    def __init__(self, max_cache_size: int = 500) -> None:
        self._actions: Dict[str, PendingAction] = {}
        self._max_cache_size = max_cache_size

    def _prune_expired_and_bounded(self) -> None:
        """Prune expired records and evict oldest if cache exceeds max size."""
        now = time.time()
        # Remove expired
        expired_keys = [k for k, v in self._actions.items() if v.expires_at < now or v.consumed]
        if len(self._actions) > self._max_cache_size:
            for k in expired_keys:
                self._actions.pop(k, None)
            # If still over limit, evict oldest
            if len(self._actions) > self._max_cache_size:
                sorted_keys = sorted(self._actions.keys(), key=lambda k: self._actions[k].created_at)
                for k in sorted_keys[: len(self._actions) - self._max_cache_size]:
                    self._actions.pop(k, None)

    async def create(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user_id: str,
        session_id: str,
        proposal_summary: str,
        ttl_seconds: float = DEFAULT_EXPIRY_SECONDS,
    ) -> PendingAction:
        """Register a new proposed action in the ledger."""
        self._prune_expired_and_bounded()
        action_id = f"act_{uuid.uuid4().hex[:12]}"
        now = time.time()
        arg_hash = compute_arguments_hash(arguments)

        action = PendingAction(
            action_id=action_id,
            tool_name=tool_name,
            arguments=dict(arguments),
            arguments_hash=arg_hash,
            user_id=user_id,
            session_id=session_id,
            proposal_summary=proposal_summary,
            created_at=now,
            expires_at=now + ttl_seconds,
            consumed=False,
            state="pending",
        )
        if db_gateway.is_connected:
            query = """
            INSERT INTO pending_actions (
                id, tool_name, arguments, arguments_hash, user_id,
                session_id, proposal_summary, consumed, state, expires_at, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """
            await db_gateway.execute_as_user(
                user_id,
                query,
                action.action_id,
                action.tool_name,
                action.arguments,
                action.arguments_hash,
                action.user_id,
                action.session_id,
                action.proposal_summary,
                action.consumed,
                action.state,
                datetime.fromtimestamp(action.expires_at, timezone.utc),
                datetime.fromtimestamp(action.created_at, timezone.utc),
            )

        self._actions[action_id] = action

        logger.info(
            f"Created pending action '{action_id}' for tool '{tool_name}' "
            f"(user={user_id}, session={session_id}, expires_in={ttl_seconds:.0f}s)"
        )
        return action

    async def get(self, action_id: str, user_id: str) -> Optional[PendingAction]:
        """Retrieve a pending action from cache or owner-scoped PostgreSQL."""
        action = self._actions.get(action_id)
        if action and action.user_id != user_id:
            return None
        if not action and db_gateway.is_connected:
            row = await db_gateway.fetchrow_as_user(
                user_id,
                "SELECT * FROM pending_actions WHERE id = $1 AND user_id = $2",
                action_id,
                user_id,
            )
            if row:
                data = dict(row)
                action = PendingAction(
                    action_id=data["id"],
                    tool_name=data["tool_name"],
                    arguments=data["arguments"] or {},
                    arguments_hash=data["arguments_hash"],
                    user_id=data["user_id"],
                    session_id=data.get("session_id") or "",
                    proposal_summary=data.get("proposal_summary") or "",
                    created_at=data["created_at"].timestamp(),
                    expires_at=data["expires_at"].timestamp(),
                    consumed=data.get("consumed", False),
                    consumed_at=data["consumed_at"].timestamp() if data.get("consumed_at") else None,
                    state=data.get("state", "pending"),
                )
                self._actions[action_id] = action
        return action

    async def get_latest_for_session(
        self, session_id: str, user_id: str
    ) -> Optional[PendingAction]:
        """Retrieve most recent unconsumed and unexpired pending action for a session/user."""
        now = time.time()
        matching = [
            a for a in self._actions.values()
            if a.session_id == session_id
            and a.user_id == user_id
            and not a.consumed
            and a.expires_at >= now
            and a.state == "pending"
        ]
        if matching:
            matching.sort(key=lambda x: x.created_at, reverse=True)
            return matching[0]

        if db_gateway.is_connected:
            row = await db_gateway.fetchrow_as_user(
                user_id,
                """SELECT * FROM pending_actions
                   WHERE session_id = $1 AND user_id = $2 AND consumed = FALSE
                     AND state = 'pending' AND expires_at >= now()
                   ORDER BY created_at DESC LIMIT 1""",
                session_id,
                user_id,
            )
            if row:
                data = dict(row)
                action = PendingAction(
                    action_id=data["id"], tool_name=data["tool_name"],
                    arguments=data["arguments"] or {}, arguments_hash=data["arguments_hash"],
                    user_id=data["user_id"], session_id=data.get("session_id") or "",
                    proposal_summary=data.get("proposal_summary") or "",
                    created_at=data["created_at"].timestamp(), expires_at=data["expires_at"].timestamp(),
                    consumed=data.get("consumed", False), consumed_at=None,
                    state=data.get("state", "pending"),
                )
                self._actions[action.action_id] = action
                return action

        return None

    async def consume(
        self,
        action_id: str,
        user_id: str,
        session_id: str,
        expected_arguments: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[str], Optional[PendingAction]]:
        """Atomically validate and consume a pending action. Prevents replay and cross-user attacks."""
        action = await self.get(action_id, user_id)
        if not action:
            return False, f"Pending action '{action_id}' not found.", None

        if action.consumed:
            return False, f"Pending action '{action_id}' has already been consumed (replay prevented).", None

        if action.is_expired():
            action.state = "expired"
            if db_gateway.is_connected:
                await db_gateway.execute_as_user(
                    user_id,
                    "UPDATE pending_actions SET consumed = TRUE, consumed_at = now(), state = 'expired' WHERE id = $1 AND user_id = $2",
                    action_id,
                    user_id,
                )
            return False, f"Pending action '{action_id}' has expired.", None

        if action.user_id != user_id:
            logger.warning(
                f"Cross-user authorization attempt blocked: user '{user_id}' attempted to confirm action belonging to '{action.user_id}'"
            )
            return False, "Authorization error: action belongs to another user.", None

        if session_id and action.session_id and action.session_id != session_id:
            logger.warning(
                f"Session mismatch: session '{session_id}' attempted to confirm action from '{action.session_id}'"
            )
            return False, "Authorization error: session mismatch.", None

        if expected_arguments is not None:
            expected_hash = compute_arguments_hash(expected_arguments)
            if expected_hash != action.arguments_hash:
                logger.warning(
                    f"Action '{action_id}' argument tampering detected: expected {expected_hash}, recorded {action.arguments_hash}"
                )
                return False, "Arguments do not match the proposed action.", None

        if db_gateway.is_connected:
            status = await db_gateway.execute_as_user(
                user_id,
                """UPDATE pending_actions
                   SET consumed = TRUE, consumed_at = now(), state = 'approved'
                   WHERE id = $1 AND user_id = $2 AND consumed = FALSE
                     AND state = 'pending' AND expires_at >= now()""",
                action_id,
                user_id,
            )
            if status != "UPDATE 1":
                return False, "Pending action is no longer available.", None

        # Mark consumed in cache after the durable authorization succeeds.
        action.consumed = True
        action.consumed_at = time.time()
        action.state = "approved"
        logger.info(f"Pending action '{action_id}' successfully consumed and authorized.")
        return True, None, action

    async def cancel(self, action_id: str, user_id: str, session_id: str = "") -> bool:
        """Mark a pending action as cancelled/rejected by user."""
        action = await self.get(action_id, user_id)
        if not action or action.consumed:
            return False
        if action.user_id != user_id:
            return False
        if session_id and action.session_id and action.session_id != session_id:
            return False
        action.consumed = True
        action.consumed_at = time.time()
        action.state = "rejected"
        if db_gateway.is_connected:
            status = await db_gateway.execute_as_user(
                user_id,
                """UPDATE pending_actions
                   SET consumed = TRUE, consumed_at = now(), state = 'rejected'
                   WHERE id = $1 AND user_id = $2 AND consumed = FALSE AND state = 'pending'""",
                action_id,
                user_id,
            )
            if status != "UPDATE 1":
                return False
        logger.info(f"Pending action '{action_id}' cancelled by user.")
        return True


# Global singleton instance
pending_action_store = PendingActionStore()

