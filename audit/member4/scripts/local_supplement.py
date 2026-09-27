"""Complete provider-independent checks after the recorded HTTP 401 limitations."""
import json
import logging
import os
from unittest.mock import patch
from urllib.parse import urlsplit

from common import ROOT, AUDIT, now, save_json
os.environ["HF_HUB_OFFLINE"] = "1"
logging.disable(logging.CRITICAL)


def main():
    from agents.knowledge_agent import rag_agent
    from agents.waste_analyzer.schemas import WasteAnalysis
    out_of_domain = json.loads((AUDIT / "evidence/json/IR-04-retrieval.json").read_text(encoding="utf-8"))
    model_input = WasteAnalysis.model_validate(out_of_domain.get("agent1_output") or out_of_domain["analysis_fixture"])
    with patch.object(rag_agent, "_get_client", side_effect=AssertionError("No provider call expected")) as get_client:
        output = rag_agent.generate_answer(model_input)
    save_json("IR-04-local-output.json", {"executed_at": now(), "mode": "real FAISS and generate_answer; labelled structured input from IR-04; provider must not be called", "provider_client_calls": get_client.call_count, "output": output})
    from backend.middleware import logging_mw
    with patch.object(logging_mw, "setup_logging"):
        from backend.main import app
    from fastapi.testclient import TestClient
    from backend.services import agent_client
    from backend.schemas import AnalysisResult, RetrievalResult, DecisionResult
    public_calls = []
    fixture_analysis = AnalysisResult(waste_types=["household"], severity="medium", location="near a school", summary="Audit fixture; not a live Agent 1 result.")
    fixture_retrieval = RetrievalResult(query="audit fixture", answer="Audit fixture response, not live generation.", grounded=False, sources=[], evidence=[])
    fixture_decision = DecisionResult(priority="medium", recommended_action="Manual review required.", confidence=0.0)
    with TestClient(app, raise_server_exceptions=False) as client:
        with patch.object(agent_client, "call_analyst", return_value=fixture_analysis), patch.object(agent_client, "call_retrieval", return_value=fixture_retrieval), patch.object(agent_client, "call_decision", return_value=fixture_decision):
            reply = client.post("/complaints/process", json={"text": "Audit synthetic household waste report."})
    save_json("IR-12-public-contract-fixture.json", {"executed_at": now(), "mode": "controlled agent-result fixtures; real route, orchestrator, validation and HTTP response; not a live AI result", "status": reply.status_code, "body": reply.json()})
    location_path = AUDIT / "evidence/json/IR-19-location.json"
    location = json.loads(location_path.read_text(encoding="utf-8"))
    location["mode"] = "Observers attached to real pipeline; only recorded fields were reached. Agent 1 provider failed before an output or Agent 2 call."
    location["limitation"] = "OpenRouter HTTP 401, independently recorded in IR-01; public route returned analyst-stage 502."
    save_json("IR-19-location.json", location)
    from backend.config import settings
    from agents.decision.agent import _get_client
    from dotenv import dotenv_values
    cfg = dotenv_values(ROOT / ".env")
    local_url = urlsplit(cfg.get("BACKEND_URL", "http://localhost:8000"))
    public_local_url = f"{local_url.scheme}://{local_url.hostname}" + (f":{local_url.port}" if local_url.port else "")
    save_json("IR-16-protocol-static.json", {
        "observed_at": now(), "mode": "Static Observation; no packet capture, remote-deployment or TLS interception test",
        "frontend_backend_url": public_local_url,
        "frontend_transport": "requests.post JSON for complaints; form POST for login; configured local HTTP",
        "agent1_openrouter_url": "https://openrouter.ai/api/v1",
        "agent2_openrouter_url": str(rag_agent._get_client().base_url),
        "groq_url": str(_get_client().base_url),
        "jwt_algorithm": settings.jwt_algorithm, "token_lifetime_minutes": settings.access_token_minutes,
        "credential_flow": "Agent 1 key goes to Agent 1 OpenRouter client, Agent 2 key to OpenRouter client, Groq key to Groq client. Backend JWT is used for local protected routes, not passed to AI prompts. No packet-level destination attestation performed.",
        "implication": "HTTP is expected for the documented localhost setup. Exposing the same configuration on an untrusted network would leave login credentials and complaint traffic without transport encryption; deploy with TLS and correct proxy configuration.",
    })
    save_json("IR-23-rate-control-static.json", {
        "observed_at": now(), "mode": "Static Observation only; no load, brute-force, flood or denial-of-service testing",
        "reviewed_files": ["backend/main.py", "backend/api/agent_routes.py", "backend/api/auth_routes.py", "backend/services/orchestrator.py"],
        "observation": "No application-level rate limit, quota or concurrency limiter found on public complaint/login/register routes in these files. CORS limits browser origins but is not an API request quota.",
        "limitation": "An external reverse proxy or hosting platform could impose limits; none is specified in this local repository. Exploitable exhaustion or real deployment limits were not tested.",
    })
    print("OOD runtime output, public contract fixture, protocol and rate-control observations saved", flush=True)


if __name__ == "__main__":
    main()
