import logging
import re
import time
import uuid

from .observability import correlation_id_var

logger = logging.getLogger("sigab.request")

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _correlation_id(incoming):
    """Accept a client request ID only when it is short and log-safe."""
    return incoming if _REQUEST_ID_PATTERN.fullmatch(incoming) else str(uuid.uuid4())


class CorrelationIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.correlation_id = _correlation_id(request.headers.get("X-Request-ID", ""))
        token = correlation_id_var.set(request.correlation_id)
        started = time.monotonic()
        try:
            response = self.get_response(request)
            response["X-Request-ID"] = request.correlation_id
            user = getattr(request, "user", None)
            authenticated = bool(user and user.is_authenticated)
            logger.info(
                "request",
                extra={
                    "correlation_id": request.correlation_id,
                    "method": request.method,
                    # Path only: query strings may carry search terms with personal data.
                    "path": request.path,
                    "status": response.status_code,
                    "duration_ms": round((time.monotonic() - started) * 1000, 1),
                    "account_id": str(user.pk) if authenticated else None,
                    "organization_id": (
                        str(user.organization_id)
                        if authenticated and user.organization_id
                        else None
                    ),
                },
            )
            return response
        finally:
            correlation_id_var.reset(token)
