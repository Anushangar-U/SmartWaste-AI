from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from pathlib import Path
import os
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.middleware.logging_mw import setup_logging, log_requests
from backend.api import auth_routes, agent_routes
from backend.auth.users import seed_admin
from backend.services.orchestrator import AgentError
from backend.database import initialize
from backend.repositories.complaints import Conflict
from backend.api import complaint_routes

@asynccontextmanager
async def lifespan(app):
    setup_logging()
    initialize()
    seed_admin()
    yield

app = FastAPI(title=settings.app_name, version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origins.split(",")],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
app.middleware("http")(log_requests)

app.include_router(auth_routes.router)
app.include_router(agent_routes.router)
app.include_router(complaint_routes.router)

@app.exception_handler(Conflict)
async def conflict_handler(request: Request, exc: Conflict):
    return JSONResponse(status_code=409, content={"detail": str(exc)})

@app.exception_handler(AgentError)
async def agent_error_handler(request: Request, exc: AgentError):
    # generic message to the client; details stay in the server log
    return JSONResponse(status_code=502,
        content={"detail": f"The {exc.stage} service is temporarily unavailable. Please retry."})

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ready")
def ready():
    from backend.database import connection
    database_ok = False
    try:
        with connection() as db:
            db.execute("SELECT 1 FROM complaints LIMIT 1")
        database_ok = True
    except Exception:
        pass
    root = Path(__file__).resolve().parents[1]
    vector_ok = all((root / "retrieval/vector_store/data" / name).is_file() for name in ["smartwaste.faiss", "metadata.json"])
    providers = {"analyst": bool(os.getenv("AGENT1_OPENROUTER_API_KEY") or settings.gemini_api_key),
                 "retrieval": bool(settings.openrouter_api_key), "decision": bool(settings.groq_api_key)}
    available = database_ok and (settings.use_mock_agents or (vector_ok and all(providers.values())))
    return JSONResponse(status_code=200 if available else 503, content={"ready": available,
        "database_reachable": database_ok, "vector_files_available": vector_ok,
        "providers_configured": providers, "mode": "mock_demo" if settings.use_mock_agents else "live",
        "note": "Configuration checks only; provider credentials and responses are not verified."})
