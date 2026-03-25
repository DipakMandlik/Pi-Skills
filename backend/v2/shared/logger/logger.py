from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import Any

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
user_id_ctx: ContextVar[str] = ContextVar("user_id", default="")


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "request_id": request_id_ctx.get(),
            "user_id": user_id_ctx.get(),
            "module": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            entry["exception"] = self.formatException(record.exc_info)
        extra = getattr(record, "extra_data", None)
        if extra:
            entry["meta"] = extra
        import json
        return json.dumps(entry, default=str)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(f"backend.v2.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
    return logger


def set_request_context(request_id: str, user_id: str = "") -> None:
    request_id_ctx.set(request_id)
    user_id_ctx.set(user_id)
