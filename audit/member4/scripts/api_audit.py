"""Local ASGI HTTP tests. No tokens, passwords, or request auth headers are saved."""
import logging
import secrets
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from common import error_record, now, save_json

logging.disable(logging.CRITICAL)
from fastapi.testclient import TestClient
from backend.middleware import logging_mw
with patch.object(logging_mw, "setup_logging"):
    from backend.main import app
from backend.auth import security
from backend.auth.users import USERS
from backend.schemas import AnalysisResult
from backend.services import agent_client

TEXT = "Household garbage has not been collected for two days."
ANALYSIS = {"waste_types": ["household"], "location": "residential street", "duration_days": 2, "severity": "medium", "issue_type": "uncollected waste", "summary": TEXT}
RETRIEVAL = {"query": "household waste", "answer": "No guidance.", "grounded": False, "sources": [], "evidence": []}
BODIES = {
    "/agents/analyze": {"text": TEXT},
    "/agents/retrieve": {"analysis": ANALYSIS},
    "/agents/decide": {"analysis": ANALYSIS, "retrieval": RETRIEVAL},
}


def result(response):
    try:
        body = response.json()
    except ValueError:
        body = response.text
    return {"status": response.status_code, "body": body}


def main():
    with TestClient(app, raise_server_exceptions=False) as client:
        # One live public request also observes selected location propagation.
        capture = {}
        original_analyst, original_retrieval = agent_client.call_analyst, agent_client.call_retrieval
        def observe_analyst(text):
            capture["analysis_input"] = text
            output = original_analyst(text)
            capture["analysis_output"] = output.model_dump(mode="json")
            return output
        def observe_retrieval(analysis):
            capture["retrieval_analysis_input"] = analysis.model_dump(mode="json")
            output = original_retrieval(analysis)
            capture["retrieval_output"] = output.model_dump(mode="json")
            return output
        try:
            from agents.waste_analyzer import agent as analyst
            from agents.knowledge_agent import rag_agent
            from agents.decision import agent as decision_agent
            with ExitStack() as stack:
                for module, method in [(analyst, "_get_openrouter_client"), (rag_agent, "_get_client"), (decision_agent, "_get_client")]:
                    bounded = getattr(module, method)().with_options(timeout=60, max_retries=0)
                    stack.enter_context(patch.object(module, method, return_value=bounded))
                stack.enter_context(patch.object(agent_client, "call_analyst", side_effect=observe_analyst))
                stack.enter_context(patch.object(agent_client, "call_retrieval", side_effect=observe_retrieval))
                reply = client.post("/complaints/process", json={"text": TEXT, "location_context": "Near a school"})
                save_json("IR-12-http.json", {"executed_at": now(), "mode": "local TestClient ASGI request, live configured AI providers, no auth", "request": {"text": TEXT, "location_context": "Near a school"}, "response": result(reply)})
            save_json("IR-19-location.json", {"executed_at": now(), "mode": "observers attached to actual agent calls within IR-12; only recorded fields were reached", "downstream_completed": "retrieval_output" in capture, **capture})
        except Exception as exc:
            save_json("IR-12-http.json", {"executed_at": now(), "limitation": error_record(exc), "mode": "live setup failed before request"})
            save_json("IR-19-location.json", {"executed_at": now(), "limitation": error_record(exc), **capture})
        print("IR-12 and IR-19 saved", flush=True)
        save_json("IR-13-http.json", {"executed_at": now(), "mode": "local ASGI HTTP, real auth dependencies", "requests": [{"route": route, "auth": "absent", **result(client.post(route, json=body))} for route, body in BODIES.items()]})
        username = "audit_m4_" + secrets.token_hex(4)
        password = secrets.token_urlsafe(24)
        try:
            register = client.post("/auth/register", json={"username": username, "password": password})
            login = client.post("/auth/login", data={"username": username, "password": password})
            token = login.json().get("access_token")
            attempted = [{"route": route, **result(client.post(route, json=body, headers={"Authorization": "Bearer " + token}))} for route, body in BODIES.items()] if token else []
            save_json("IR-14-http.json", {"executed_at": now(), "mode": "temporary in-memory account; random credential and token never persisted", "registration": result(register), "login": result(login), "requests": attempted})
        finally:
            USERS.pop(username, None)
        with patch("backend.auth.security.datetime") as clock:
            clock.now.return_value = datetime.now(timezone.utc) - timedelta(days=7)
            expired = security.create_access_token("audit_expired", "admin")
        auth_cases = [
            ("invalid fake JWT", "Bearer audit.invalid.signature"),
            ("wrong authorization scheme", "Basic audit-placeholder"),
            ("empty bearer", "Bearer"),
            ("expired project-generated token", "Bearer " + expired),
        ]
        save_json("IR-15-http.json", {"executed_at": now(), "requests": [{"case": name, "route": "/agents/analyze", **result(client.post("/agents/analyze", json={"text": TEXT}, headers={"Authorization": header}))} for name, header in auth_cases]})
        invalid = [
            ("empty JSON", {}), ("missing text", {"location_context": "Near a school"}),
            ("wrong text type", {"text": ["garbage"]}), ("empty text", {"text": ""}),
            ("whitespace only", {"text": " " * 10}), ("short text", {"text": "waste"}),
            ("2001 characters", {"text": "x" * 2001}),
            ("location wrong type", {"text": TEXT, "location_context": ["school"]}),
            ("location 121 characters", {"text": TEXT, "location_context": "x" * 121}),
        ]
        save_json("IR-16-invalid-input.json", {"executed_at": now(), "mode": "real request validation; whitespace reaches actual Agent 1 blank-input guard without an external call", "requests": [{"case": name, "input": body, **result(client.post("/complaints/process", json=body))} for name, body in invalid]})
        failure_results = []
        for label, error in [("provider timeout", TimeoutError("audit-timeout-marker")), ("provider error", RuntimeError("audit-error-marker"))]:
            with patch.object(agent_client, "call_analyst", return_value=AnalysisResult(**ANALYSIS)), patch.object(agent_client, "call_retrieval", side_effect=error):
                failure_results.append({"case": label, **result(client.post("/complaints/process", json={"text": TEXT}))})
        save_json("IR-22-provider-failures.json", {"executed_at": now(), "mode": "controlled provider-boundary exceptions; real orchestrator and exception handler", "requests": failure_results})
        print("IR-13 through IR-16 and IR-22 saved", flush=True)


if __name__ == "__main__":
    main()
