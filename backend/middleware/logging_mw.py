import logging, os, time, uuid
from contextvars import ContextVar
from fastapi import Request

def setup_logging():
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.FileHandler("logs/app.log"), logging.StreamHandler()],
    )

access_log = logging.getLogger("smartwaste.access")
correlation_id = ContextVar("correlation_id", default="offline")

async def log_requests(request: Request, call_next):
    rid = str(uuid.uuid4())
    token = correlation_id.set(rid)
    start = time.perf_counter()
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        ms = (time.perf_counter() - start) * 1000
        # Route template prevents tracking capabilities from entering this log.
        route = getattr(request.scope.get("route"), "path", "unmatched")
        access_log.info("rid=%s %s %s -> %d (%.0fms)", rid, request.method,
                        route, response.status_code, ms)
        return response
    finally:
        correlation_id.reset(token)
