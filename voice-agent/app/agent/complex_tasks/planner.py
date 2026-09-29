"""Task decomposition and planning engine for complex multi-step workflows."""

import logging
from typing import Any, Dict, List, Optional

from app.agent.complex_tasks.state import TaskStep
from app.integrations.composio.client import composio_gateway

logger = logging.getLogger(__name__)


class ComplexTaskPlanner:
    """Decomposes high-level composite requests into concrete executable tool steps."""

    async def plan_steps(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        user_id: str = "default_user",
    ) -> List[TaskStep]:
        """Generate an ordered plan of sub-steps based on user goal and connected skills."""
        ctx = context or {}

        # 1. Dynamic skill resolution via Composio Gateway
        try:
            skill_steps = await composio_gateway.resolve_skill_steps(
                goal=goal,
                entity_id=user_id,
                context=ctx,
            )
            if skill_steps:
                steps: List[TaskStep] = []
                for idx, step_dict in enumerate(skill_steps, start=1):
                    steps.append(
                        TaskStep(
                            step_id=idx,
                            description=step_dict.get("description", f"Step {idx}"),
                            tool_name=step_dict.get("tool_name", "web_search_serpapi"),
                            arguments=step_dict.get("arguments", {}),
                            status="pending",
                            result=None,
                        )
                    )
                logger.info(f"Planned {len(steps)} steps via Composio skills for goal: '{goal}'")
                return steps
        except Exception:
            logger.exception("Error resolving steps via Composio skills; falling back to heuristic planner.")

        # 2. Fallback heuristic planning
        steps = self._fallback_heuristic_plan(goal, ctx)
        logger.info(f"Planned {len(steps)} steps via fallback heuristics for goal: '{goal}'")
        return steps

    def _fallback_heuristic_plan(self, goal: str, context: Dict[str, Any]) -> List[TaskStep]:
        """Deterministic rule-based planning fallback when dynamic skills are unavailable."""
        goal_lower = goal.lower()
        steps: List[TaskStep] = []

        if "email" in goal_lower and ("doc" in goal_lower or "note" in goal_lower):
            steps.append(
                TaskStep(
                    step_id=1,
                    description="Search relevant emails for requested topic",
                    tool_name="search_emails",
                    arguments={"query": context.get("query", goal)},
                    status="pending",
                    result=None,
                )
            )
            steps.append(
                TaskStep(
                    step_id=2,
                    description="Save findings into Google Doc",
                    tool_name="manage_google_doc",
                    arguments={
                        "title": context.get("title", f"Summary: {goal[:30]}"),
                        "content": context.get("content", "Summary of findings..."),
                    },
                    status="pending",
                    result=None,
                )
            )

        elif "email" in goal_lower and ("sheet" in goal_lower or "spreadsheet" in goal_lower or "log" in goal_lower):
            steps.append(
                TaskStep(
                    step_id=1,
                    description="Search inbox for relevant messages",
                    tool_name="search_emails",
                    arguments={"query": context.get("query", "is:unread")},
                    status="pending",
                    result=None,
                )
            )
            steps.append(
                TaskStep(
                    step_id=2,
                    description="Log email records into Google Sheet",
                    tool_name="manage_google_sheet",
                    arguments={
                        "spreadsheet_id": context.get("spreadsheet_id", "active_sheet"),
                        "action": "append",
                        "values": context.get("values", ["Subject", "Sender", "Date"]),
                    },
                    status="pending",
                    result=None,
                )
            )

        elif ("search" in goal_lower or "research" in goal_lower) and "meeting" in goal_lower:
            steps.append(
                TaskStep(
                    step_id=1,
                    description="Perform web research via Perplexity",
                    tool_name="perplexity_ai_research",
                    arguments={"prompt": context.get("query", goal)},
                    status="pending",
                    result=None,
                )
            )
            steps.append(
                TaskStep(
                    step_id=2,
                    description="List upcoming calendar slots for discussion",
                    tool_name="list_calendar_events",
                    arguments={"max_events": context.get("max_events", 5)},
                    status="pending",
                    result=None,
                )
            )

        elif "email" in goal_lower and ("reply" in goal_lower or "draft" in goal_lower or "send" in goal_lower):
            steps.append(
                TaskStep(
                    step_id=1,
                    description="Search for targeted email thread",
                    tool_name="search_emails",
                    arguments={"query": context.get("query", goal)},
                    status="pending",
                    result=None,
                )
            )
            steps.append(
                TaskStep(
                    step_id=2,
                    description="Send email response",
                    tool_name="send_email",
                    arguments={
                        "recipient": context.get("recipient", "the recipient"),
                        "subject": f"Re: {context.get('subject', 'Update')}",
                        "body": context.get("body", "Drafted response."),
                    },
                    status="pending",
                    result=None,
                )
            )

        elif "notion" in goal_lower and ("doc" in goal_lower or "page" in goal_lower or "note" in goal_lower or "save" in goal_lower):
            steps.append(
                TaskStep(
                    step_id=1,
                    description=f"Gather information for '{goal}'",
                    tool_name="web_search_serpapi",
                    arguments={"query": context.get("query", goal)},
                    status="pending",
                    result=None,
                )
            )
            steps.append(
                TaskStep(
                    step_id=2,
                    description="Create notes page in Notion",
                    tool_name="execute_app_action",
                    arguments={
                        "app_name": "notion",
                        "intent": "create",
                        "parameters": {
                            "title": context.get("title", f"Notes: {goal[:30]}"),
                            "content": context.get("content", "Synthesized findings..."),
                        },
                    },
                    status="pending",
                    result=None,
                )
            )

        elif any(app in goal_lower for app in ("teams", "whatsapp", "telegram")) and any(act in goal_lower for act in ("send", "message", "notify")):
            target_app = "microsoft_teams" if "teams" in goal_lower else ("whatsapp" if "whatsapp" in goal_lower else "telegram")
            steps.append(
                TaskStep(
                    step_id=1,
                    description=f"Send notification message via {target_app.replace('_', ' ').title()}",
                    tool_name="execute_app_action",
                    arguments={
                        "app_name": target_app,
                        "intent": "send",
                        "parameters": {
                            "message": context.get("message", goal),
                            "recipient": context.get("recipient", "general"),
                        },
                    },
                    status="pending",
                    result=None,
                )
            )

        elif "drive" in goal_lower and any(kw in goal_lower for kw in ("search", "find", "locate")):
            steps.append(
                TaskStep(
                    step_id=1,
                    description="Search Google Drive for matching files",
                    tool_name="search_google_drive",
                    arguments={"query": context.get("query", goal), "max_results": 5},
                    status="pending",
                    result=None,
                )
            )

        else:
            steps.append(
                TaskStep(
                    step_id=1,
                    description=f"Gather information for '{goal}'",
                    tool_name="web_search_serpapi",
                    arguments={"query": goal},
                    status="pending",
                    result=None,
                )
            )
            steps.append(
                TaskStep(
                    step_id=2,
                    description="Save summarized findings to memory",
                    tool_name="save_memory",
                    arguments={"content": f"Researched '{goal}'", "category": "research"},
                    status="pending",
                    result=None,
                )
            )

        return steps


complex_task_planner = ComplexTaskPlanner()
