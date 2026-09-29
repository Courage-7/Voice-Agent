"""Dynamic verbal turn-holding and progressive task feedback engine.

Generates ultra-low-latency (<5ms), context-aware, organic verbal fillers
to hold the conversational turn over TTS during asynchronous tool executions
(e.g., email retrieval, calendar lookups, web research, workspace actions).
Eliminates dead air without robotic or stiff repetition.
"""

from __future__ import annotations

import hashlib
import re
from typing import List, Optional


def _extract_sender(text: str) -> Optional[str]:
    """Extract a person's name or sender from email queries."""
    match = re.search(r"\bfrom\s+([A-Z][a-z]+|[a-z]+)\b", text, re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        if name.lower() not in ("me", "my", "the", "yesterday", "today", "recent", "any", "all"):
            return name.capitalize()
    return None


def _extract_timeframe(text: str) -> Optional[str]:
    """Extract temporal reference from calendar queries."""
    match = re.search(
        r"\b(tomorrow\s+(?:morning|afternoon|evening)|today\s+(?:morning|afternoon|evening)|tomorrow|today|this\s+(?:week|afternoon|evening|morning)|next\s+week|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).lower().strip()
    return None


def _extract_search_topic(text: str) -> Optional[str]:
    """Extract research topic from web search queries."""
    # Match patterns like "search the web for X", "look up X", "latest news on X"
    match = re.search(
        r"(?:search(?:\s+(?:the\s+web|online|google))?(?:\s+for)?|look\s+up|research|find\s+out\s+about|latest\s+(?:news|updates?)\s+on)\s+(.+)",
        text,
        re.IGNORECASE,
    )
    if match:
        topic = match.group(1).strip()
        # Clean trailing question marks or punctuation
        topic = re.sub(r"[?!.]+$", "", topic).strip()
        if len(topic) > 3 and not topic.lower().startswith("what"):
            return topic[:40]
    return None


def get_contextual_verbal_filler(user_text: str, turn_seed: int = 0) -> Optional[str]:
    """Return an organic, context-aware verbal turn-holding filler phrase.

    Returns ``None`` if the turn is purely conversational and does not trigger
    external tool execution (so the LLM can stream its response directly).
    """
    if not user_text:
        return None

    clean = user_text.strip()
    lower = clean.lower()

    # Deterministic rotation seed based on text hash and turn seed
    salt = int(hashlib.md5((clean + str(turn_seed)).encode("utf-8")).hexdigest(), 16)

    # 1. Email Lookup & Synthesis
    is_email = bool(re.search(r"\b(gmail|emails?|inbox|messages?)\b", lower))
    has_email_action = bool(re.search(r"\b(find|check|search|look|pull\s+up|read|see|get)\b", lower))

    if is_email and has_email_action:
        sender = _extract_sender(clean)
        if sender:
            variations = [
                f"Sure, let me check your messages from {sender}...",
                f"Looking through your inbox for emails from {sender}...",
                f"Pulling up recent emails from {sender} right now...",
                f"Let me check what emails {sender} sent you recently...",
            ]
        else:
            variations = [
                "Sure, let me check your recent emails...",
                "Looking through your inbox right now...",
                "Checking your mail real quick...",
                "On it, pulling up your latest messages...",
                "Let me see what's in your inbox...",
            ]
        return variations[salt % len(variations)]

    # 2. Calendar Check & Scheduling
    is_cal = bool(re.search(r"\b(calendar|schedule|agenda|events?|meetings?|free\s+time|availability)\b", lower))
    has_cal_action = bool(re.search(r"\b(check|find|look|what|see|do\s+i\s+have|free|open)\b", lower))

    if is_cal and (has_cal_action or "schedule" in lower or "calendar" in lower):
        timeframe = _extract_timeframe(clean)
        if timeframe:
            variations = [
                f"Let me take a quick look at your calendar for {timeframe}...",
                f"Checking your schedule for {timeframe}...",
                f"Let me see what you have booked for {timeframe}...",
                f"Checking your availability for {timeframe} right now...",
            ]
        else:
            variations = [
                "Pulling up your calendar right now...",
                "Let me check your schedule real quick...",
                "Looking at your upcoming events...",
                "Checking your calendar for you...",
            ]
        return variations[salt % len(variations)]

    # 3. Web Search & Research
    is_search = bool(re.search(
        r"\b(search\s+(?:the\s+web|online|google)|look\s+up|research|find\s+out|latest\s+(?:news|updates?|headlines))\b",
        lower,
    ))

    if is_search:
        topic = _extract_search_topic(clean)
        if topic:
            variations = [
                f"Looking that up for you right now...",
                f"Let me search for the latest on {topic}...",
                f"Checking recent reports on {topic}...",
                f"Let me search what's currently reported on {topic}...",
            ]
        else:
            variations = [
                "Looking that up for you right now...",
                "Searching online real quick...",
                "Let me check the web for that...",
                "Pulling up the latest search information now...",
            ]
        return variations[salt % len(variations)]

    # 4. Workspace Documents / Drive
    is_docs = bool(re.search(r"\b(google\s+docs?|sheets?|drive|spreadsheets?|documents?)\b", lower))
    if is_docs and has_email_action:
        variations = [
            "Searching your workspace files right now...",
            "Let me look through your documents for that...",
            "Checking your Google Drive real quick...",
        ]
        return variations[salt % len(variations)]

    # Pure conversational turn (no external tool filler needed)
    return None
