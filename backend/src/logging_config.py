import contextvars
import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional

_PHONE_E164_RE = re.compile(r"\+\d{7,15}")


class PhoneMaskFilter(logging.Filter):
    """Mask E.164 phone numbers in log messages before emission."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _PHONE_E164_RE.sub("+***", record.msg)
        # Also mask pre-formatted args strings if args were already applied
        if record.args:
            try:
                formatted = record.getMessage()
                masked = _PHONE_E164_RE.sub("+***", formatted)
                record.msg = masked
                record.args = ()
            except Exception:
                pass
        return True


request_id_ctx_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)
campaign_id_ctx_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("campaign_id", default=None)
request_path_ctx_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_path", default=None)
http_method_ctx_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("http_method", default=None)


class RequestContextFilter(logging.Filter):
    """Inject request and campaign correlation data into log records."""

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover - simple passthrough
        record.request_id = request_id_ctx_var.get()
        record.campaign_id = campaign_id_ctx_var.get()
        record.request_path = request_path_ctx_var.get()
        record.http_method = http_method_ctx_var.get()
        return True


class JsonFormatter(logging.Formatter):
    """Format log records as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - formatting only
        log_payload: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.request_id:
            log_payload["request_id"] = record.request_id
        if record.campaign_id:
            log_payload["campaign_id"] = record.campaign_id
        if record.request_path:
            log_payload["path"] = record.request_path
        if record.http_method:
            log_payload["method"] = record.http_method

        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload)


def setup_logging() -> None:
    """Configure global structured logging."""

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestContextFilter())
    handler.addFilter(PhoneMaskFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))
    root_logger.handlers = [handler]
    root_logger.propagate = False


def set_campaign_context(campaign_id: Optional[int]) -> contextvars.Token:
    """Set campaign correlation id in context."""

    value = str(campaign_id) if campaign_id is not None else None
    return campaign_id_ctx_var.set(value)


def reset_campaign_context(token: contextvars.Token) -> None:
    """Reset campaign correlation context after use."""

    campaign_id_ctx_var.reset(token)
