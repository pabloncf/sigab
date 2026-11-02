import json
import logging
import re
import traceback
from contextvars import ContextVar
from datetime import UTC, datetime

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

# Fields copied from `extra=` into the JSON line; anything else is dropped so that
# request objects, payloads or model instances never reach the technical log.
ALLOWED_EXTRA_FIELDS = (
    "method",
    "path",
    "status",
    "duration_ms",
    "account_id",
    "organization_id",
)

_CPF_PATTERN = re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)")
_SECRET_PATTERN = re.compile(
    r"(?i)\b(password|senha|token|secret|csrfmiddlewaretoken|sessionid|authorization)"
    r"(\s*[=:]\s*|\"\s*:\s*\")[^\s&\"',;]+"
)


def redact(text):
    """Remove CPF-like numbers and secret assignments from free text."""
    text = _CPF_PATTERN.sub("[cpf]", text)
    return _SECRET_PATTERN.sub(lambda match: f"{match.group(1)}{match.group(2)}[redacted]", text)


class CorrelationIdFilter(logging.Filter):
    def filter(self, record):
        # django.request logs after the middleware returns, so fall back to the request.
        if not getattr(record, "correlation_id", ""):
            request = getattr(record, "request", None)
            record.correlation_id = correlation_id_var.get() or getattr(
                request, "correlation_id", ""
            )
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record):
        entry = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact(record.getMessage()),
            "correlation_id": getattr(record, "correlation_id", "") or correlation_id_var.get(),
        }
        for field in ALLOWED_EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                entry[field] = value
        if record.exc_info:
            exc_type = record.exc_info[0]
            entry["error_type"] = exc_type.__name__ if exc_type else ""
            entry["traceback"] = redact("".join(traceback.format_exception(*record.exc_info)))
        return json.dumps(entry, ensure_ascii=False)
