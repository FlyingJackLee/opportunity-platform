"""Structured logging per spec §87 (fields: timestamp/run_id/event_id/node/duration/
status/model/token_usage/error). `@log_node` wraps every graph node so Phase 2+
nodes get this instrumentation for free instead of re-adding it per node."""

import functools
import logging
import time
from collections.abc import Awaitable, Callable

import structlog
from structlog.contextvars import bind_contextvars, bound_contextvars

from app.core.config import Settings


def configure_logging(settings: Settings) -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", key="timestamp"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def bind_run_context(run_id: str, event_id: str | None = None) -> None:
    bind_contextvars(run_id=run_id, event_id=event_id)


def log_llm_usage(
    logger: structlog.stdlib.BoundLogger,
    *,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    logger.info(
        "llm_call",
        model=model,
        token_usage={"input_tokens": input_tokens, "output_tokens": output_tokens},
    )


def log_node(
    name: str,
) -> Callable[[Callable[..., Awaitable[dict]]], Callable[..., Awaitable[dict]]]:
    """Decorator for LangGraph node callables `(state) -> dict`. Binds node=name,
    times execution, logs one line on exit with duration_ms/status; re-raises on
    error after logging so runner.py's outer handler still sets the run FAILED."""

    def decorator(fn: Callable[..., Awaitable[dict]]) -> Callable[..., Awaitable[dict]]:
        @functools.wraps(fn)
        async def wrapper(state: dict) -> dict:
            logger = structlog.get_logger()
            start = time.perf_counter()
            with bound_contextvars(node=name):
                try:
                    result = await fn(state)
                except Exception as exc:
                    duration_ms = round((time.perf_counter() - start) * 1000, 2)
                    logger.error(
                        "node_failed",
                        duration_ms=duration_ms,
                        status="error",
                        error=str(exc),
                    )
                    raise
                duration_ms = round((time.perf_counter() - start) * 1000, 2)
                logger.info("node_completed", duration_ms=duration_ms, status="ok")
                return result

        return wrapper

    return decorator
