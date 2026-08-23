"""Application logging configuration and structured log formatting."""

import logging
import sys
from app.core.config import settings


def setup_logging() -> None:
    """Configure structured logger."""
    log_format = "%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
    )


logger = logging.getLogger("voice_agent")
