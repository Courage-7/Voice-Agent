"""Unit tests for the dynamic verbal turn-holding feedback engine."""

import pytest
from app.agent.verbal_feedback import (
    get_contextual_verbal_filler,
    _extract_sender,
    _extract_timeframe,
    _extract_search_topic,
)


def test_extract_sender():
    assert _extract_sender("Can you find that email from Sarah?") == "Sarah"
    assert _extract_sender("Look for messages from Alex about Q3") == "Alex"
    assert _extract_sender("Check emails from me") is None


def test_extract_timeframe():
    assert _extract_timeframe("What do I have tomorrow afternoon?") == "tomorrow afternoon"
    assert _extract_timeframe("Check my schedule for next week") == "next week"
    assert _extract_timeframe("Do I have any meetings today?") == "today"


def test_extract_search_topic():
    assert "SpaceX" in (_extract_search_topic("Search the web for SpaceX launch updates") or "")
    assert "Fed meeting" in (_extract_search_topic("Look up latest news on Fed meeting") or "")


def test_email_query_with_sender():
    filler = get_contextual_verbal_filler("Hey, can you search my emails from Alex?")
    assert filler is not None
    assert "Alex" in filler
    assert any(w in filler.lower() for w in ("inbox", "email", "messages", "mail"))


def test_email_query_general():
    filler = get_contextual_verbal_filler("Please check my recent emails")
    assert filler is not None
    assert any(w in filler.lower() for w in ("inbox", "email", "messages", "mail"))


def test_calendar_query_with_timeframe():
    filler = get_contextual_verbal_filler("Check my calendar for tomorrow afternoon")
    assert filler is not None
    assert "tomorrow afternoon" in filler
    assert any(w in filler.lower() for w in ("calendar", "schedule", "availability", "booked"))


def test_web_search_query():
    filler = get_contextual_verbal_filler("Search the web for the latest SpaceX launch update")
    assert filler is not None
    assert any(w in filler.lower() for w in ("search", "looking", "checking", "latest", "web"))


def test_conversational_turn_returns_none():
    assert get_contextual_verbal_filler("Hello there! How are you today?") is None
    assert get_contextual_verbal_filler("Thanks for the help!") is None
    assert get_contextual_verbal_filler("What is the capital of France?") is None


def test_variety_rotation():
    query = "Check my recent emails"
    phrases = {get_contextual_verbal_filler(query, turn_seed=i) for i in range(10)}
    # Assert at least 3 distinct phrasing variations
    assert len(phrases) >= 3
