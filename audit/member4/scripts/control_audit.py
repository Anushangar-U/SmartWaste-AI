"""Execute production controls with explicit audit fixtures; never modify source."""
import json
import logging
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from common import ROOT, AUDIT, error_record, now, save_json
os.environ["HF_HUB_OFFLINE"] = "1"
logging.disable(logging.CRITICAL)

from agents.knowledge_agent import rag_agent as rag
from agents.waste_analyzer.schemas import WasteAnalysis
from agents.decision import agent as decision_agent
from agents.decision.rules import validate_decision
from backend.services import agent_client
from backend.schemas import AnalysisResult, RetrievalResult
from retrieval.vector_store import faiss_store, retriever


def analysis():
    return WasteAnalysis(waste_types=["household"], location="residential street", duration_days=2, severity="medium", issue_type="uncollected waste", summary="Household garbage has not been collected for two days.")


def recommendation(**changes):
    value = {"priority": "medium", "recommended_action": "Schedule collection.", "explanation": "Routine collection guidance.", "supporting_sources": ["guide.pdf"], "requires_human_review": False, "confidence": 0.85}
    value.update(changes)
    return value


def fake_client(content, calls):
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def threshold():
    chunks = [{"chunk_id": f"audit_{score}", "source": "guide.pdf", "page": page, "text": f"Audit fixture passage at score {score}.", "score": score} for page, score in enumerate([0.34, 0.35, 0.36], 1)]
    captured = []
    with patch.object(rag, "retrieve_for_analysis", return_value={"query": "household waste", "evidence": chunks}), patch.object(rag, "_get_client", return_value=fake_client("Audit fixture response [1].", captured)):
        output = rag.generate_answer(analysis())
    decision_calls = []
    with patch.object(decision_agent, "_get_client", return_value=fake_client(json.dumps(recommendation()), decision_calls)):
        downstream = agent_client.call_decision(AnalysisResult.model_validate(analysis().model_dump()), RetrievalResult.model_validate(output))
    empty_calls = []
    with patch.object(rag, "retrieve_for_analysis", return_value={"query": "unrelated", "evidence": chunks[:1]}), patch.object(rag, "_get_client", return_value=fake_client("unused", empty_calls)):
        empty = rag.generate_answer(analysis())
    save_json("IR-08-threshold.json", {"executed_at": now(), "mode": "Executed Test - controlled boundary scores; real generate_answer and decision adapter", "input_evidence": chunks, "generation_calls": captured, "output": output, "downstream_prompt": decision_calls, "downstream_output": downstream.model_dump(mode="json"), "no_qualifying_output": empty, "no_qualifying_generation_calls": len(empty_calls)})


def decisions():
    evidence = [{"source": "guide.pdf", "text": "Medical and hazardous waste reference guidance."}]
    routine = "Household garbage has not been collected from a residential street for two days."
    hazardous = "Several leaking chemical containers and used syringes have been dumped beside a school near the river since yesterday."
    records = []
    for name, text in [("routine", routine), ("hazardous", hazardous), ("explicit negation", "This is ordinary household garbage. It is not chemical waste, not medical waste, not hazardous waste, and there are no syringes.")]:
        value, issues = validate_decision(recommendation(explanation="No hazardous or medical waste is reported.", recommended_action="Routine collection; no chemical team required."), evidence, analysis=analysis().model_dump(), complaint_text=text)
        records.append({"case": name, "complaint": text, "decision": value, "issues": issues})
    save_json("IR-17-review-rules.json", {"executed_at": now(), "mode": "Executed Test - real deterministic validator with labelled model-prose fixture", "cases": records})
    outputs = []
    for label, content in [("empty model output", None), ("invalid JSON", "not JSON"), ("incomplete JSON", '{"priority": "medium"}'), ("invented citation", json.dumps(recommendation(supporting_sources=["invented-audit-source.pdf"])) )]:
        with patch.object(decision_agent, "_get_client", return_value=fake_client(content, [])):
            output = decision_agent.decide(analysis().model_dump(), evidence, complaint_text=routine)
        outputs.append({"case": label, "output": output})
    save_json("IR-18-decision-controls.json", {"executed_at": now(), "mode": "Executed Test - injected provider responses; real parser/rules", "cases": outputs})


def faiss_controls():
    import numpy as np
    records = [{"chunk_id": f"audit_{i}", "source": "fixture.pdf", "page": 1, "text": "audit fixture", "embedding": [1.0 if j == i else 0.0 for j in range(384)]} for i in range(3)]
    index, metadata = faiss_store.build_index(records)
    faiss_store.validate_index(index, metadata, expected_vector_count=3)
    output = {"executed_at": now(), "mode": "Executed Test - three-vector temporary corpus, no real index edits", "valid_corpus": {"vectors": index.ntotal, "dimension": index.d, "index_type": type(index).__name__, "validated": True}}
    with tempfile.TemporaryDirectory(dir=AUDIT / "scripts") as directory:
        path = Path(directory)
        try:
            faiss_store.load_index(store_dir=path)
        except Exception as exc:
            output["missing_store"] = error_record(exc)
        faiss_store.save_index(index, metadata[:-1], store_dir=path)
        loaded = faiss_store.load_index(store_dir=path)
        with patch.object(retriever, "_load_vector_store", return_value=(loaded["index"], loaded["metadata"])):
            try:
                retriever.retrieve("household waste")
            except Exception as exc:
                output["mismatched_store"] = error_record(exc)
    save_json("IR-21-faiss-controls.json", output)


def frontend_control():
    record = {"executed_at": now(), "mode": "Executed Test - Streamlit AppTest; synthetic session presence only, no bearer token or credentials; no browser JS execution"}
    try:
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(ROOT / "frontend/app.py"), default_timeout=20)
        at.session_state["view_mode"] = "staff"
        at.session_state["auth_token"] = True
        at.session_state["auth_username"] = "audit_display"
        payload = "<script>alert('audit')</script><b>garbage</b>"
        at.session_state["complaints"] = [{"id": "audit_display", "text": payload, "location": "<school>", "submitted_at": "audit time", "priority": "medium", "recommended_action": "<img src=x onerror=alert('audit')>"}]
        at.run()
        rows = [item.value for item in at.markdown if 'class="swa-row"' in item.value]
        record.update({"exception_count": len(at.exception), "rendered_rows": rows, "raw_script_present": any("<script>" in row for row in rows), "escaped_script_present": any("&lt;script&gt;" in row for row in rows), "raw_img_present": any("<img" in row for row in rows)})
    except Exception as exc:
        record["limitation"] = error_record(exc)
    save_json("IR-20-rendering.json", record)


def grounding_boundary():
    source = AUDIT / "evidence/json/IR-01-retrieval.json"
    evidence = json.loads(source.read_text(encoding="utf-8"))["qualifying_by_threshold"]
    unsupported = "The municipality is legally required to collect this household garbage within exactly 17 hours under Audit Fiction Rule 999 [1]."
    captured = []
    with patch.object(rag, "retrieve_for_analysis", return_value={"query": "household waste", "evidence": evidence}), patch.object(rag, "_get_client", return_value=fake_client(unsupported, captured)):
        output = rag.generate_answer(analysis())
    save_json("IR-24-grounding-boundary.json", {"executed_at": now(), "mode": "Executed Test - deliberately unsupported provider-response fixture; NOT a live model hallucination", "fixture_answer": unsupported, "output": output, "phrase_in_evidence": any("Audit Fiction Rule 999" in item["text"] for item in evidence), "actual_provider_called": False})


if __name__ == "__main__":
    for function in (threshold, decisions, faiss_controls, frontend_control, grounding_boundary):
        function()
        print(function.__name__, "saved", flush=True)
