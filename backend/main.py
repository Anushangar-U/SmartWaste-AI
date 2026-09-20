from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.middleware.logging_mw import setup_logging, log_requests
from backend.api import auth_routes, agent_routes
from backend.auth.users import seed_admin
from backend.services.orchestrator import AgentError

setup_logging()
seed_admin()

app = FastAPI(title=settings.app_name, version="0.1.0")

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

@app.exception_handler(AgentError)
async def agent_error_handler(request: Request, exc: AgentError):
    # generic message to the client; details stay in the server log
    return JSONResponse(status_code=502,
        content={"detail": f"The {exc.stage} service is temporarily unavailable. Please retry."})

@app.get("/health")
def health():
    return {"status": "ok"}