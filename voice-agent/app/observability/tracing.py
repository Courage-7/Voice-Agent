"""Session tracing and correlation manager."""

import logging
from uuid import uuid4

logger = logging.getLogger(__name__)


def generate_trace_id() -> str:
    """Generate a unique correlation trace ID."""
    return str(uuid4())
