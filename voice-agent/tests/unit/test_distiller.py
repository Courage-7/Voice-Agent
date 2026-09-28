"""Unit tests for Speech Payload Distiller & Token Budgeting Gateway."""

import json
from app.tools.distiller import SpeechPayloadDistiller, speech_payload_distiller


def test_distiller_under_character_budget():
    """Verify standard tool output is returned cleanly and safely under budget."""
    raw = {
        "success": True,
        "spoken_summary": "Found 2 upcoming meetings.",
        "count": 2,
    }
    result_str = speech_payload_distiller.distill("list_calendar_events", raw)
    assert len(result_str) <= 1200
    data = json.loads(result_str)
    assert data["success"] is True
    assert data["spoken_summary"] == "Found 2 upcoming meetings."
    assert data["count"] == 2


def test_distiller_email_pruning():
    """Verify bloated email lists are pruned to compact spoken fields."""
    raw_emails = [
        {
            "sender": f"colleague{i}@company.com",
            "subject": f"Project Sync Update Number {i}",
            "preview": "A" * 500,  # massive body
            "raw_headers": {"X-Tracking": "123" * 20},
            "attachments": ["file1.pdf", "file2.png"],
        }
        for i in range(10)
    ]
    raw = {
        "success": True,
        "spoken_summary": "Here are your unread emails.",
        "emails": raw_emails,
    }
    result_str = speech_payload_distiller.distill("list_emails", raw)
    assert len(result_str) <= 1200
    data = json.loads(result_str)
    assert data["success"] is True
    assert len(data["emails"]) <= 4
    for em in data["emails"]:
        assert len(em["snippet"]) <= 100
        assert "raw_headers" not in em
        assert "attachments" not in em


def test_distiller_massive_payload_hard_limit():
    """Verify that even a 50KB arbitrary JSON payload is strictly compacted under 1200 chars."""
    huge_data = {
        "success": True,
        "spoken_summary": "Completed large document search.",
        "raw_blob": "X" * 50000,
        "results": [{"title": f"Doc {i}", "text": "Y" * 1000} for i in range(20)],
    }
    result_str = speech_payload_distiller.distill("manage_google_doc", huge_data, max_chars=1200)
    assert len(result_str) <= 1200
    data = json.loads(result_str)
    assert data["success"] is True


def test_distiller_error_and_confirmation():
    """Verify confirmation prompts and error strings are preserved concisely."""
    confirmation_payload = {
        "success": True,
        "requires_confirmation": True,
        "message": "Send email to bob@example.com with subject 'Meeting'?",
        "spoken_summary": "I'm ready to send that email.",
    }
    conf_str = speech_payload_distiller.distill("send_email", confirmation_payload)
    conf_data = json.loads(conf_str)
    assert conf_data["requires_confirmation"] is True
    assert "bob@example.com" in conf_data["message"]

    error_payload = {
        "success": False,
        "error": "Authentication token expired. Please re-authenticate via Composio OAuth.",
        "spoken_summary": "Your Google connection expired.",
    }
    err_str = speech_payload_distiller.distill("list_calendar_events", error_payload)
    err_data = json.loads(err_str)
    assert err_data["success"] is False
    assert "expired" in err_data["error"]
