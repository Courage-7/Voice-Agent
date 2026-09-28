"""Provider-agnostic task state machine for grounded capability execution."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional
from uuid import uuid4

from app.integrations.composio.client import composio_gateway
from app.tools.capability import canonical_app_slug, is_account_active
from app.tools.registry import ToolRegistry, tool_registry

ActivityCallback = Callable[[Dict[str, Any]], Awaitable[None]]
logger = logging.getLogger(__name__)


class TaskState(StrEnum):
    PLANNED = "planned"
    ACCESS_RESOLVED = "access_resolved"
    EXECUTING = "executing"
    VALIDATING = "validating"
    RECONCILING = "reconciling"
    COMPLETE = "complete"
    FAILED = "failed"
    NEEDS_INPUT = "needs_input"


TERMINAL_STATES = {TaskState.COMPLETE, TaskState.FAILED, TaskState.NEEDS_INPUT}


@dataclass
class CapabilityTask:
    """A planned operation with an explicit, validated completion state."""

    goal: str
    tool_name: str
    capability: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    allows_empty: bool = True
    id: str = field(default_factory=lambda: str(uuid4()))
    state: TaskState = TaskState.PLANNED
    result: Optional[Dict[str, Any]] = None
    failure_code: Optional[str] = None


@dataclass(frozen=True)
class ExecutionSummary:
    connected_apps: List[str]
    tasks: List[CapabilityTask]

    @property
    def complete(self) -> bool:
        return all(task.state == TaskState.COMPLETE for task in self.tasks)


class CapabilityExecutionEngine:
    """Resolve, bind, execute, and validate tasks independently of providers.

    Provider-specific account compatibility belongs to tool adapters through
    ``BaseTool.supported_connected_apps``. This engine only sees capabilities,
    operations, authenticated identity, and task state.
    """

    def __init__(self, registry: ToolRegistry = tool_registry) -> None:
        self.registry = registry

    async def execute(
        self,
        tasks: Iterable[CapabilityTask],
        *,
        user_id: str,
        session_id: str,
        on_activity: Optional[ActivityCallback] = None,
    ) -> ExecutionSummary:
        task_list = list(tasks)
        try:
            accounts = await composio_gateway.get_connected_accounts(entity_id=user_id)
        except Exception:
            logger.exception("Connected-account resolution failed for authenticated user")
            for task in task_list:
                self._fail(task, "connection_resolution_failed", "I could not verify access to the requested connected service.")
            return ExecutionSummary(connected_apps=[], tasks=task_list)
        connected_apps = sorted({
            canonical_app_slug(str(account.get("app") or ""))
            for account in accounts
            if is_account_active(str(account.get("status") or ""))
            and account.get("is_active", True)
        } - {""})
        capabilities = sorted({task.capability for task in task_list})
        bound_tools = {
            tool.name: tool
            for tool in self.registry.get_tools_for_capabilities(
                capabilities=capabilities,
                connected_apps=connected_apps,
            )
        }

        ready: List[CapabilityTask] = []
        for task in task_list:
            registered_tool = self.registry.get_tool(task.tool_name)
            if registered_tool is None:
                self._fail(task, "capability_unavailable", f"No registered capability can perform {task.goal}.")
                continue
            if task.tool_name not in bound_tools:
                code = "connection_unavailable" if registered_tool.supported_connected_apps else "capability_unavailable"
                self._fail(task, code, f"No authorized connected capability can perform {task.goal}.")
                continue
            task.state = TaskState.ACCESS_RESOLVED
            ready.append(task)

        parallel = [task for task in ready if bound_tools[task.tool_name].supports_parallel_execution]
        serial = [task for task in ready if not bound_tools[task.tool_name].supports_parallel_execution]
        if parallel:
            await asyncio.gather(*[
                self._execute_one(task, user_id, session_id, on_activity)
                for task in parallel
            ])
        for task in serial:
            await self._execute_one(task, user_id, session_id, on_activity)

        return ExecutionSummary(connected_apps=connected_apps, tasks=task_list)

    async def _execute_one(
        self,
        task: CapabilityTask,
        user_id: str,
        session_id: str,
        on_activity: Optional[ActivityCallback],
    ) -> None:
        task.state = TaskState.EXECUTING
        await self._emit(on_activity, {
            "type": "FunctionCallRequest",
            "functions": [{"name": task.tool_name, "arguments": task.arguments}],
            "task_id": task.id,
            "capability": task.capability,
            "activity": f"Executing {task.goal}",
        })
        result = await self.registry.execute_tool(
            tool_name=task.tool_name,
            arguments=task.arguments,
            user_id=user_id,
            session_id=session_id,
        )
        task.result = result
        task.state = TaskState.VALIDATING
        self._validate(task)
        await self._emit(on_activity, {
            "type": "FunctionCallResult",
            "name": task.tool_name,
            "task_id": task.id,
            "capability": task.capability,
            "success": task.state == TaskState.COMPLETE,
            "status": task.state.value,
            "failure_code": task.failure_code,
        })

    def _validate(self, task: CapabilityTask) -> None:
        result = task.result or {}
        if not result.get("success"):
            status = str(result.get("status") or "request_failed")
            if result.get("requires_disambiguation"):
                task.state = TaskState.NEEDS_INPUT
                task.failure_code = "provider_selection_required"
            elif status in {"connection_unavailable", "authorization_error", "unavailable"}:
                task.state = TaskState.FAILED
                task.failure_code = status
            else:
                task.state = TaskState.FAILED
                task.failure_code = "request_failed"
            return

        if not task.allows_empty and not self._contains_result_data(result):
            self._fail(task, "incomplete_result", f"{task.goal} returned no usable data.")
            return
        task.state = TaskState.RECONCILING
        # Result normalization/reconciliation is performed by the caller's
        # domain presenter; this explicit transition prevents transport success
        # from being treated as completion before that handoff.
        task.state = TaskState.COMPLETE

    @staticmethod
    def _contains_result_data(result: Dict[str, Any]) -> bool:
        for key in ("items", "emails", "events", "data"):
            value = result.get(key)
            if isinstance(value, (list, tuple, dict)) and bool(value):
                return True
        return bool(result.get("count"))

    @staticmethod
    def _fail(task: CapabilityTask, code: str, message: str) -> None:
        task.state = TaskState.FAILED
        task.failure_code = code
        task.result = {"success": False, "status": code, "error": message, "spoken_summary": message}

    @staticmethod
    async def _emit(callback: Optional[ActivityCallback], event: Dict[str, Any]) -> None:
        if callback:
            try:
                await callback(event)
            except Exception:
                # Observability must not prevent a user-authorized operation.
                logger.exception("Capability activity event could not be delivered")


capability_execution_engine = CapabilityExecutionEngine()
