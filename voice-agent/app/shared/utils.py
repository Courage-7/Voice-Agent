"""Shared helper utilities for audio conversion, text cleanup, and formatting."""

import re
from typing import Any, Tuple


def extract_dual_stream_tags(text: str) -> Tuple[str, str]:
    """Extract display markdown and speech text from dual-stream XML tags.
    
    Returns (display_markdown, speech_text). If tags are absent, returns
    (text, clean_voice_text(text)) as a resilient fallback.
    """
    if not text:
        return "", ""

    def _get_tag_content(tag: str) -> str:
        start_tag = f"<{tag}>"
        end_tag = f"</{tag}>"
        if start_tag not in text:
            return ""
        start_idx = text.find(start_tag) + len(start_tag)
        end_idx = text.find(end_tag)
        if end_idx != -1:
            return text[start_idx:end_idx].strip()
        return text[start_idx:].strip()

    display = _get_tag_content("display")
    speech = _get_tag_content("speech")

    if not display and not speech:
        # Fallback when model omitted XML tags
        display = text.strip()
        speech = clean_voice_text(text)
    elif not speech and display:
        speech = clean_voice_text(display)
    elif not display and speech:
        display = speech

    return display, speech


def clean_voice_text(text: str) -> str:
    """Strip markdown symbols, XML tags, hashtags, and URLs for TTS vocalization safety."""
    if not text:
        return ""
    # Strip XML tags if present
    cleaned = re.sub(r"</?(?:display|speech)[^>]*>", "", text)
    # Remove markdown headers, bold, italics, backticks, math delimiters
    cleaned = re.sub(r"[#*_`~$]", "", cleaned)
    # Remove bullet point dashes at line starts
    cleaned = re.sub(r"^\s*[-+*]\s+", "", cleaned, flags=re.MULTILINE)
    # Remove raw URLs so TTS doesn't read them aloud
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    # Collapse multiple whitespaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def format_iso_timestamp(dt: Any) -> str:
    """Format datetime object into clean ISO 8601 string."""
    if hasattr(dt, "isoformat"):
        return dt.isoformat()
    return str(dt)

