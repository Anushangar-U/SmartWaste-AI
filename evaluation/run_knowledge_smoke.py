"""Offline smoke evaluation for the committed knowledge corpus.

Run after rebuilding the local FAISS store. This uses the real MiniLM embeddings and
FAISS index but makes no external LLM/API calls.
"""
from __future__ import annotations

import json

from retrieval.processing.quality import rerank, deduplicate
from retrieval.sources import display_metadata
from retrieval.vector_store.retriever import retrieve


CASES = [
    {
        "name": "sri_lanka_scheduled_chemical",
        "query": "Sri Lanka hazardous scheduled chemical waste storage collection transport disposal licensed facility",
        "expected_sources": {"Guidelines-Book.pdf"},
    },
    {
        "name": "lead_acid_battery",
        "query": "Sri Lanka used leaking lead acid battery collection licensed recycler battery acid",
        "expected_sources": {"Battery_waste_Guidelines.pdf"},
    },
    {
        "name": "lithium_battery",
        "query": "lithium ion battery damaged swollen fire hazard disposal recycle electronics",
        "expected_sources": {
            "Lithium-Ion-Batteries-Fact-Sheet-8-2023.pdf",
            "Guideline for the importation of used EV batteries.pdf",
        },
    },
    {
        "name": "medical_sharps",
        "query": "health care medical sharps needles puncture injury infectious waste disposal",
        "expected_sources": {
            "WHO-FWC-WSH-17.05-eng.pdf",
            "9789241516228-eng.pdf",
            "who_un_environment_guidance.pdf",
        },
    },
    {
        "name": "chemical_incident",
        "query": "chemical incident exposure inhalation skin contamination decontamination emergency response",
        "expected_sources": {"9789241598149_eng.pdf", "9241546115_eng.pdf"},
    },
    {
        "name": "sri_lanka_municipal",
        "query": "Sri Lanka municipal solid waste collection transport composting landfill local authority",
        "expected_sources": {
            "Guidlines-on-solid-waste-management.pdf",
            "sri_lanka_plastic_action_plan.pdf",
        },
    },
]


def evaluate_case(case):
    candidates = retrieve(case["query"], top_k=30)
    selected = deduplicate(rerank(candidates, case["query"], top_k=10), top_k=5)
    sources = [item["source"] for item in selected]
    matched = sorted(set(sources) & case["expected_sources"])
    return {
        "name": case["name"],
        "query": case["query"],
        "pass": bool(matched),
        "matched_expected_sources": matched,
        "top_sources": [
            {
                "filename": item["source"],
                "title": display_metadata(item["source"]).get("title"),
                "page": item["page"],
                "score": round(float(item["score"]), 4),
            }
            for item in selected
        ],
    }


def main():
    results = [evaluate_case(case) for case in CASES]
    report = {
        "cases": results,
        "passed": sum(item["pass"] for item in results),
        "total": len(results),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if report["passed"] != report["total"]:
        failed = ", ".join(item["name"] for item in results if not item["pass"])
        raise SystemExit(f"Knowledge smoke evaluation failed: {failed}")


if __name__ == "__main__":
    main()
