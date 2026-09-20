import logging, os, time, uuid
from fastapi import Request

def setup_logging():
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.FileHandler("logs/app.log"), logging.StreamHandler()],
    )

access_log = logging.getLogger("smartwaste.access")

async def log_requests(request: Request, call_next):
    rid = str(uuid.uuid4())[:8]
    start = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - start) * 1000
    # method, path, status only. Never log bodies or Authorization headers.
    access_log.info("rid=%s %s %s -> %d (%.0fms)", rid, request.method,
                    request.url.path, response.status_code, ms)
    return response