"""Task decomposition and planning engine for complex multi-step workflows."""

import logging
from typing import Any, Dict, List
from uuid import uuid4

from app.agent.complex_tasks.state import TaskStep

logger = logging.getLogger(__name__)


class ComplexTaskPlanner:
    """Decomposes high-level composite requests into concrete executable tool steps."""

    def plan_steps(self, goal: str, context: Dict[str, Any]) -> List[TaskStep]:
        """Generate an ordered plan of sub-steps based on user goal."""
        goal_lower = goal.lower()
        steps: List[TaskStep] = []

        # Pattern 1: Search emails + create note / doc
        if "email" in goal_lower and ("doc" in goal_lower or "note" in goal_lower or "sheet" in goal_lower):
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
                    arguments={"title": f"Summary: {goal[:30]}", "content": "Summary of findings..."},
                    status="pending",
                    result=None,
                )
            )

        # Pattern 2: Search web + schedule meeting / follow up
        elif ("search" in goal_lower or "research" in goal_lower) and "meeting" in goal_lower:
            steps.append(
                TaskStep(
                    step_id=1,
                    description="Perform web research via Perplexity",
                    tool_name="perplexity_research",
                    arguments={"query": context.get("query", goal)},
                    status="pending",
                    result=None,
                )
            )
            steps.append(
                TaskStep(
                    step_id=2,
                    description="List upcoming calendar slots for discussion",
                    tool_name="list_calendar_events",
                    arguments={"max_events": 5},
                    status="pending",
                    result=None,
                )
            )

        # Pattern 3: Email overview + draft response
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

        # Generic Multi-Step Fallback
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

        logger.info(f"Planned {len(steps)} steps for complex task: '{goal}'")
        return steps


complex_task_planner = ComplexTaskPlanner()
