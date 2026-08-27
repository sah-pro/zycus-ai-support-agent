"""Lightweight structured logging.

Logs operational metadata (request id, operation, latency, model, prompt
version, retrieval count, success/failure) as single-line JSON. Never logs
raw ticket/account content by default -- only identifiers and counts -- to
avoid leaking customer data into log aggregation systems.
"""
from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from contextlib import contextmanager
from typing import Any, Iterator

from src.config.settings import settings

_logger = logging.getLogger("zycus_ai_support")
if not _logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(handler)
_logger.setLevel(settings.log_level)


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


@contextmanager
def log_operation(operation: str, request_id: str | None = None, **fields: Any) -> Iterator[dict]:
    """Context manager that logs a single structured JSON line per operation.

    Usage:
        with log_operation("triage", ticket_id=t.ticket_id) as log:
            ...
            log["retrieval_count"] = 3
    """
    request_id = request_id or new_request_id()
    start = time.monotonic()
    payload: dict[str, Any] = {"request_id": request_id, "operation": operation, **fields}
    success = True
    try:
        yield payload
    except Exception as exc:
        success = False
        payload["error"] = str(exc)
        raise
    finally:
        payload["latency_ms"] = round((time.monotonic() - start) * 1000, 2)
        payload["success"] = success
        _logger.info(json.dumps(payload, default=str))
