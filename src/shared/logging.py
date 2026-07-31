from __future__ import annotations

import logging
import os
import sys

import structlog


def setup_logging(level: str = "info") -> None:
    """Configure structured logging with JSON output for production.

    Outputs JSON with timestamp, level, request_id, and user_id fields
    for log aggregation and correlation. Falls back to console renderer
    when running interactively in development.
    """
    # Use JSON renderer in production (non-TTY or explicitly set)
    force_json = os.environ.get("LOG_FORMAT", "").lower() == "json"
    use_json = force_json or not sys.stderr.isatty()

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", key="timestamp"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if use_json:
        shared_processors.append(structlog.processors.JSONRenderer())
    else:
        shared_processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )


def bind_request_context(request_id: str | None = None, user_id: str | None = None) -> None:
    """Bind request_id and user_id to the structlog context for correlation."""
    if request_id:
        structlog.contextvars.bind_contextvars(request_id=request_id)
    if user_id:
        structlog.contextvars.bind_contextvars(user_id=user_id)


def clear_request_context() -> None:
    """Clear request-scoped context variables."""
    structlog.contextvars.clear_contextvars()
