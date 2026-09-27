"""Real corpus/ranking audit; optional fixtures are explicitly labelled in evidence."""
import argparse
import logging
import os
from collections import Counter
from unittest.mock import patch

from common import ROOT, error_record, now, save_json

os.environ["HF_HUB_OFFLINE"] = "1"  # use the installed model cache; no model downloads
logging.disable(logging.CRITICAL)

from agents.waste_analyzer import agent as analyst
from agents.waste_analyzer.schemas import WasteAnalysis
from agents.knowledge_agent import rag_agent as rag
from retrieval.vector_store.faiss_store import load_index

ROUTINE = "Household garbage has not been collected from a residential street for two days."
CASES = {
    "IR-01": (ROUTINE, ["household"], "residential street", 2, "uncollected waste"),
    "IR-02": ("Several leaking chemical containers and used syringes have been dumped beside a school near the river since yesterday.", ["chemical", "medical"], "beside a school near the river", 1, "dumping"),
    "IR-03": ("There is some waste near my area and it has been there for a while.", ["mixed"], "unknown", None, "waste accumulation"),
    "IR-04": ("How should I maintain my laptop battery to maximize its lifespan during everyday use?", [], "unknown", None, "laptop battery maintenance"),
    "IR-05": (ROUTINE + " chemical hazardous syringe toxic hospital river school chemical hazardous syringe", ["household", "chemical", "hazardous", "syringe"], "residential street", 2, "uncollected waste"),
    "IR-06": ("This is ordinary household garbage. It is not chemical waste, not medical waste, not hazardous waste, and there are no syringes.", ["household"], "unknown", None, "household garbage"),
    "IR-07": ("Garbage has been dumped beside a school near the river for three days.", ["mixed"], "beside a school near the river", 3, "dumping"),
    "IR-11": ("What exact number of hours does Sri Lankan national law require a municipal crew to collect household garbage after a citizen submits an online complaint? Cite the law and clause. If no source gives this exact deadline, say so.", ["household"], "Sri Lanka", None, "legal collection deadline after online complaint"),
}
GENERATE = {"IR-01", "IR-02", "IR-03", "IR-04", "IR-06", "IR-11"}


def corpus_search():
    import pymupdf
    import re
    from retrieval.ingest import clean_text

    results = []
    for path in sorted((ROOT / "retrieval/documents").glob("*.pdf")):
        with pymupdf.open(path) as doc:
            hits = []
            for page_number, page in enumerate(doc, 1):
                text = clean_text(page.get_text())
                # Search every extractable page before attempting IR-11.
                patterns = {
                    "complaint": r"complain\w*.{0,180}",
                    "deadline": r".{0,80}deadline.{0,180}",
                    "hours": r".{0,100}\b(?:\d+|twenty.four|forty.eight)\s*hours?\b.{0,150}",
                    "online": r".{0,70}\bonline\b.{0,120}",
                }
                matches = {label: re.findall(pattern, text, flags=re.I | re.S)[:12] for label, pattern in patterns.items()}
                if any(matches.values()):
                    hits.append({"page": page_number, "matches": matches})
            results.append({"source": path.name, "page_count": len(doc), "hits": hits})
    save_json("IR-11-corpus-search.json", {"executed_at": now(), "method": "Search all extractable PDF pages; matches are candidate passages, not legal conclusions.", "documents": results})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", nargs="*", default=list(CASES))
    parser.add_argument("--corpus-only", action="store_true")
    args = parser.parse_args()
    corpus_search()
    if args.corpus_only:
        return
    store = load_index()
    save_json("vector-store.json", {
        "captured_at": now(), "index_type": type(store["index"]).__name__,
        "dimension": store["index"].d, "vectors": store["index"].ntotal,
        "metadata_records": len(store["metadata"]),
        "source_chunk_counts": dict(Counter(item["source"] for item in store["metadata"])),
        "build_info_present": (ROOT / "retrieval/vector_store/data/build_info.json").exists(),
    })
    analyst_blocked = None
    generation_blocked = None
    for test_id in args.cases:
        text, waste_types, location, duration, issue = CASES[test_id]
        record = {"test_id": test_id, "executed_at": now(), "input": text, "transport_limit": "Audit-only 60 second request timeout, zero SDK retries. Production source and model unchanged."}
        print(test_id, "starting", flush=True)
        if analyst_blocked:
            record["agent1_limitation"] = analyst_blocked
        else:
            try:
                if analyst.AGENT1_OPENROUTER_API_KEY:
                    bounded = analyst._get_openrouter_client().with_options(timeout=60, max_retries=0)
                    with patch.object(analyst, "_get_openrouter_client", return_value=bounded):
                        analysis = analyst.analyze_complaint(text)
                else:
                    analysis = analyst.analyze_complaint(text)
                record["agent1_mode"] = "live configured provider"
                record["agent1_output"] = analysis.model_dump(mode="json")
            except Exception as exc:
                record["agent1_limitation"] = error_record(exc)
                if getattr(exc, "status_code", 0) in (401, 402, 429, 503):
                    analyst_blocked = record["agent1_limitation"]
        if "agent1_output" not in record:
            analysis = WasteAnalysis(waste_types=waste_types, location=location, duration_days=duration, severity="medium", issue_type=issue, summary=text)
            record["agent1_mode"] = "audit-authored structured fixture; NOT Agent 1 output"
            record["analysis_fixture"] = analysis.model_dump(mode="json")
        try:
            before = rag.retrieve_for_analysis(analysis)
            record["retrieval_query"] = before["query"]
            record["before_filter"] = before["evidence"]
            record["qualifying_by_threshold"] = [item for item in before["evidence"] if item["score"] >= rag.MIN_EVIDENCE_SCORE]
            record["threshold"] = rag.MIN_EVIDENCE_SCORE
            # Direct raw-query comparison isolates retriever sensitivity from Agent 1.
            record["direct_complaint_ranking"] = rag.retrieve(text, top_k=5)
            if test_id in GENERATE and generation_blocked is None:
                try:
                    client = rag._get_client().with_options(timeout=60, max_retries=0)
                    original_create = client.chat.completions.create
                    def observed_create(**kwargs):
                        record["generation_messages"] = kwargs["messages"]
                        reply = original_create(**kwargs)
                        record["returned_model"] = reply.model
                        return reply
                    with patch.object(rag, "_get_client", return_value=client), patch.object(client.chat.completions, "create", side_effect=observed_create):
                        record["rag_output"] = rag.generate_answer(analysis)
                    record["generation_mode"] = "live configured provider (unless no qualifying evidence)"
                except Exception as exc:
                    record["generation_limitation"] = error_record(exc)
                    if getattr(exc, "status_code", 0) in (401, 402, 429, 503):
                        generation_blocked = record["generation_limitation"]
            elif test_id in GENERATE:
                record["generation_limitation"] = {"not_attempted_after_provider_failure": generation_blocked}
            else:
                record["generation_mode"] = "not requested: ranking/query test"
        except Exception as exc:
            record["retrieval_limitation"] = error_record(exc)
        save_json(f"{test_id}-retrieval.json", record)
        print(test_id, "saved", record.get("agent1_mode"), "retained", len(record.get("qualifying_by_threshold", [])), "generation", bool(record.get("rag_output")), flush=True)


if __name__ == "__main__":
    main()
