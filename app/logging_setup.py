"""Shared logging configuration for CLI entrypoints."""

from __future__ import annotations

import logging
import os
import time

DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s:%(lineno)d %(message)s"
DEFAULT_LOG_DATEFMT = "%Y-%m-%dT%H:%M:%S%z"


def configure_logging(level: str | None = None) -> None:
    """Configure logging with a unified format and timestamp."""
    log_level = (level or os.environ.get("LOG_LEVEL", "INFO")).upper()
    log_format = os.environ.get("LOG_FORMAT", DEFAULT_LOG_FORMAT)
    log_datefmt = os.environ.get("LOG_DATEFMT", DEFAULT_LOG_DATEFMT)
    use_utc = os.environ.get("LOG_UTC", "1").lower() in {"1", "true", "yes"}
    if use_utc:
        logging.Formatter.converter = time.gmtime

    logging.basicConfig(level=log_level, format=log_format, datefmt=log_datefmt)
