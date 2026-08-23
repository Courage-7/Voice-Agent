"""Shared helper utilities for audio conversion, text cleanup, and formatting."""

import re
from typing import Any, Dict


def clean_voice_text(text: str) -> str:
    """Strip markdown symbols, bolding, hashtags, and emojis from text for TTS safety."""
    # Remove markdown headers, bold, italics, backticks
    cleaned = re.sub(r"[#*_`~]", "", text)
    # Remove bullet point dashes at line starts
    cleaned = re.sub(r"^\s*[-+*]\s+", "", cleaned, flags=re.MULTILINE)
    # Collapse multiple whitespaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def format_iso_timestamp(dt: Any) -> str:
    """Format datetime object into clean ISO 8601 string."""
    if hasattr(dt, "isoformat"):
        return dt.isoformat()
    return str(dt)
