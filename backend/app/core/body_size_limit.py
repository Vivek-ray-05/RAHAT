"""
Rejects any request body over MAX_BODY_BYTES before it's read into
memory -- nothing in this API needs a large payload (the biggest
legitimate body is a citizen report's description text), so this
just closes off an easy resource-exhaustion vector.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

MAX_BODY_BYTES = 1_000_000  # 1MB


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None and int(content_length) > MAX_BODY_BYTES:
            return JSONResponse(status_code=413, content={"detail": "Request body too large"})
        return await call_next(request)
