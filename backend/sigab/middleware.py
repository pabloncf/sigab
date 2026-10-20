import uuid


class CorrelationIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.headers.get("X-Request-ID", "")
        request.correlation_id = incoming[:64] if incoming else str(uuid.uuid4())
        response = self.get_response(request)
        response["X-Request-ID"] = request.correlation_id
        return response
