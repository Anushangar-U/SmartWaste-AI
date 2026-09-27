"""Bounded single-process controls for the default university/demo deployment."""
import threading
import time
from collections import deque
from contextlib import contextmanager
from fastapi.responses import JSONResponse
from backend.config import settings

_lock = threading.Lock()
_requests = {}
_active = 0


def allow(key, limit, timestamp=None):
    stamp = time.monotonic() if timestamp is None else timestamp
    with _lock:
        for old_key in list(_requests):
            queue = _requests[old_key]
            while queue and queue[0] <= stamp - 60:
                queue.popleft()
            if not queue:
                del _requests[old_key]
        if key not in _requests and len(_requests) >= 2000:
            return False
        queue = _requests.setdefault(key, deque())
        if len(queue) >= limit:
            return False
        queue.append(stamp)
        return True


@contextmanager
def processing_slot():
    global _active
    with _lock:
        admitted = _active < settings.max_concurrent_processing
        if admitted:
            _active += 1
    try:
        yield admitted
    finally:
        if admitted:
            with _lock:
                _active -= 1


async def resource_limits(request, call_next):
    path = request.url.path
    if request.method == "POST" and path in {"/complaints", "/complaints/process", "/auth/login", "/auth/register"}:
        bucket = "auth" if path.startswith("/auth/") else "submission"
        limit = settings.auth_requests_per_minute if bucket == "auth" else settings.public_requests_per_minute
        peer = request.client.host if request.client else "unknown"
        # Forwarded client headers are deliberately not trusted.
        if not allow((bucket, peer), limit):
            return JSONResponse(status_code=429, content={"detail":"Request limit reached; retry shortly."}, headers={"Retry-After":"60"})
    return await call_next(request)


class BodySizeLimit:
    """ASGI receive wrapper caps request bodies even without Content-Length."""
    def __init__(self, app, maximum=16384):
        self.app, self.maximum = app, maximum

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in {"POST","PATCH","PUT"}:
            return await self.app(scope, receive, send)
        messages, length = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            length += len(message.get("body", b""))
            if length > self.maximum:
                return await JSONResponse(status_code=413, content={"detail":"Request body is too large."})(scope, receive, send)
            messages.append(message)
            if not message.get("more_body", False):
                break
        async def replay():
            return messages.pop(0) if messages else await receive()
        await self.app(scope, replay, send)
