import argparse
import csv
import hashlib
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from evaluation.metrics import evaluate

ROOT = Path(__file__).resolve().parents[1]


def redact(value):
    from dotenv import dotenv_values
    import os
    encoded = json.dumps(value, ensure_ascii=False)
    for key, secret in {**dotenv_values(ROOT / ".env"), **os.environ}.items():
        if re.search(r"KEY|SECRET|PASSWORD|TOKEN", key, re.I) and isinstance(secret, str) and len(secret) >= 6:
            encoded = encoded.replace(json.dumps(secret, ensure_ascii=False)[1:-1], "[REDACTED]")
    return json.loads(re.sub(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", "[REDACTED]", encoded))


def predict(case, task, variant):
    from backend.config import settings
    from backend.schemas import AnalysisResult, RetrievalResult
    from backend.services import agent_client
    if task == "retrieval":
        from retrieval.vector_store.retriever import retrieve
        from retrieval.processing.quality import deduplicate
        results = retrieve(case["text"], top_k=15 if variant == "deduplicated" else 5)
        if variant == "deduplicated":
            results = deduplicate(results, 5)
        return {"retrieval": {"evidence": [r for r in results if r["score"] >= 0.35]}, "api_calls_estimate": 0}
    if variant == "rules":
        from agents.decision.triage import hazard_mentions
        affirmative, uncertain = hazard_mentions(case["text"])
        return {"decision": {"priority": "high" if affirmative else "medium", "requires_human_review": affirmative or uncertain}, "api_calls_estimate": 0}
    if settings.use_mock_agents:
        raise ValueError("Live evaluation requires USE_MOCK_AGENTS=false")
    if task == "agent1":
        return {"analysis": agent_client.call_analyst(case["text"]).model_dump(mode="json"), "api_calls_estimate": 1}
    if task == "decision":
        analysis = AnalysisResult.model_validate(case["input_analysis"])
        retrieval = RetrievalResult.model_validate(case["input_retrieval"])
        result = agent_client.call_decision(analysis, retrieval, case["text"])
        return {"decision": result.model_dump(mode="json"), "retrieval": retrieval.model_dump(mode="json"), "api_calls_estimate": 1}
    from backend.services.orchestrator import process_complaint
    result = process_complaint(case["text"]).model_dump(mode="json")
    result["api_calls_estimate"] = 2 + int(bool(result["retrieval"]["evidence"]))
    return result


def main(task):
    parser = argparse.ArgumentParser(description="Evaluate only human-reviewed cases. No live calls by default.")
    parser.add_argument("--dataset", type=Path, default=ROOT / "evaluation/complaints.reviewed.json")
    parser.add_argument("--predictions", type=Path, help="Score saved outputs without calling any provider")
    parser.add_argument("--variant", choices=["baseline", "deduplicated", "rules"], default="baseline")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--split", choices=["development", "holdout"], help="Restrict to a split; keep holdout separate from tuning")
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation/results" / task)
    args = parser.parse_args()
    records = json.loads(args.dataset.read_text(encoding="utf-8"))
    if args.split:
        records = [r for r in records if r.get("split") == args.split]
    if args.variant == "deduplicated" and task != "retrieval":
        raise SystemExit("The deduplicated variant applies only to retrieval evaluation")
    if args.variant == "rules" and task not in {"decision", "system"}:
        raise SystemExit("The rules baseline applies only to decision/system evaluation")
    if len({r["id"] for r in records}) != len(records):
        raise SystemExit("Duplicate case IDs are not allowed")
    eligible = [r for r in records if r.get("review_status") == "REVIEWED"]
    if any(not r.get("reviewer") or not r.get("reviewed_at") for r in eligible):
        raise SystemExit("REVIEWED cases must record reviewer and reviewed_at")
    if args.limit < 1:
        raise SystemExit("Limit must be positive")
    predictions = json.loads(args.predictions.read_text(encoding="utf-8")) if args.predictions else {}
    if not args.predictions and eligible:
        if task != "retrieval" and args.variant != "rules" and not args.live:
            raise SystemExit("Use --live for provider calls, --predictions for saved outputs, or --variant rules.")
        for case in eligible[:args.limit]:
            started = time.perf_counter()
            try:
                prediction = predict(case, task, args.variant)
                prediction["output_sha256"] = hashlib.sha256(json.dumps(prediction, sort_keys=True).encode()).hexdigest()
            except Exception as exc:
                cause = exc
                while cause.__cause__ is not None:
                    cause = cause.__cause__
                prediction = {"error": type(exc).__name__, "http_status": getattr(cause, "status_code", None)}
            prediction["latency_seconds"] = time.perf_counter() - started
            predictions[case["id"]] = redact(prediction)
            if prediction.get("http_status") in {401,403,429}:
                break  # Do not repeatedly hit invalid credentials or exhausted quota.
    result = evaluate(records, predictions)
    result.update({"task": task, "variant": args.variant, "executed_at": datetime.now(timezone.utc).isoformat(),
        "git_sha": subprocess.check_output(["git","rev-parse","HEAD"], cwd=ROOT, text=True).strip(),
        "dataset_sha256": hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
        "status": "NO_REVIEWED_CASES" if not eligible else "EVALUATED",
        "notes": "Null metrics have no eligible denominator. API calls are estimates excluding SDK retries. No monetary cost is inferred."})
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "summary.json").write_text(json.dumps(redact(result), indent=2), encoding="utf-8")
    (args.output / "predictions.json").write_text(json.dumps(redact(predictions), indent=2), encoding="utf-8")
    with (args.output / "metrics.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file); writer.writerow(["metric","value","n"])
        writer.writerows((name,metric["value"],metric["n"]) for name,metric in result["metrics"].items())
    lines = ["# Evaluation result", "", result["status"], "", "| Metric | Value | n |", "|---|---:|---:|"]
    lines.extend(f"| {name} | {metric['value'] if metric['value'] is not None else 'Not available'} | {metric['n']} |" for name,metric in result["metrics"].items())
    (args.output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(result["status"], "reviewed:", len(eligible), "evaluated:", result["evaluated_records"])
