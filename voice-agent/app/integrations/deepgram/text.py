"""Presentation-safe text normalization for Deepgram voice events."""

import re


def normalize_for_speech(text: str) -> str:
    """Convert display-oriented content into natural spoken language."""
    if not text:
        return ""
    cleaned = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    cleaned = re.sub(r'[\u2600-\u27bf\u2300-\u23ff\u2b50\ufe0f\u200d]', '', cleaned)
    cleaned = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', cleaned)
    cleaned = re.sub(r'`([^`]+)`', r'\1', cleaned)
    cleaned = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cleaned)
    cleaned = re.sub(r'^#{1,6}\s+', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'^\s*[-*•]\s+', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'\$\$(.*?)\$\$', r'\1', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'\$(.*?)\$', r'\1', cleaned)
    cleaned = re.sub(r'\\\[(.*?)\\\]', r'\1', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'\\\((.*?)\\\)', r'\1', cleaned)
    cleaned = re.sub(r'\*{1,3}', '', cleaned)
    return re.sub(r'[ \t]{2,}', ' ', cleaned).strip()


def normalize_for_display(text: str) -> str:
    """Prepare concise, safe Markdown for the transcript UI."""
    if not text:
        return ""
    cleaned = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    cleaned = re.sub(r'[\u2600-\u27bf\u2300-\u23ff\u2b50\ufe0f\u200d]', '', cleaned)
    cleaned = re.sub(r'^#{1,6}\s+', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', cleaned)
    return re.sub(r'\*{1,3}', '', cleaned).strip()
