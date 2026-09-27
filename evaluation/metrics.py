"""Metrics only consume REVIEWED records. Null means no eligible denominator."""
from collections import defaultdict
from statistics import mean


def evaluate(records, predictions):
    samples = defaultdict(list)
    tp = fp = fn = 0
    waste_cases = 0
    reviewed = [r for r in records if r.get("review_status") == "REVIEWED"]
    for case in reviewed:
        pred = predictions.get(case["id"])
        if pred is None:
            continue
        samples["provider_failure_rate"].append(bool(pred.get("error")))
        if pred.get("latency_seconds") is not None:
            samples["latency_seconds"].append(pred["latency_seconds"])
        if pred.get("api_calls_estimate") is not None:
            samples["api_calls_estimate"].append(pred["api_calls_estimate"])
        if pred.get("error"):
            continue
        ref = case.get("reference", {})
        analysis = pred.get("analysis", {})
        expected = ref.get("agent1", {})
        for field in ["severity", "issue_type", "location", "duration_days"]:
            if field in expected and "analysis" in pred:
                samples[field + "_agreement"].append(analysis.get(field) == expected[field])
        if "waste_types" in expected and "analysis" in pred:
            actual = {s.lower().strip() for s in analysis.get("waste_types", [])}
            target = {s.lower().strip() for s in expected["waste_types"]}
            tp += len(actual & target); fp += len(actual - target); fn += len(target - actual)
            waste_cases += 1
        retrieval = pred.get("retrieval", {})
        if "retrieval" in pred:
            evidence = retrieval.get("evidence", [])
            samples["abstention_rate"].append(not evidence)
            labels = ref.get("retrieval", {})
            judgments = labels.get("relevance", {})
            keys = [e["chunk_id"] if e["chunk_id"] in judgments else e["source"] for e in evidence]
            # Unjudged results never silently become irrelevant labels.
            if judgments and all(key in judgments for key in keys):
                for k in [1,3,5]:
                    samples[f"precision_at_{k}"].append(sum(judgments[key] == "relevant" for key in keys[:k]) / k)
                    samples[f"graded_precision_at_{k}"].append(sum({"relevant":1,"partially_relevant":0.5,"irrelevant":0}[judgments[key]] for key in keys[:k]) / k)
                rank = next((i for i,key in enumerate(keys[:5], 1) if judgments[key] == "relevant"), None)
                samples["mrr_at_5"].append(1 / rank if rank else 0)
                relevant = {key for key, label in judgments.items() if label == "relevant"}
                if labels.get("relevant_ids_complete") and relevant:
                    samples["recall_at_5"].append(len(set(keys[:5]) & relevant) / len(relevant))
            if "expected_abstain" in labels:
                samples["correct_abstention"].append((not evidence) == labels["expected_abstain"])
            if labels.get("out_of_domain") is True:
                samples["out_of_domain_rejection"].append(not evidence)
        decision = pred.get("decision", {})
        expected_decision = ref.get("decision", {})
        if "decision" in pred:
            if "priority" in expected_decision:
                samples["priority_agreement"].append(decision.get("priority") == expected_decision["priority"])
            if "review_required" in expected_decision:
                required = decision.get("requires_human_review", True)
                samples["review_trigger_accuracy"].append(required == expected_decision["review_required"])
                if not expected_decision["review_required"]:
                    samples["unnecessary_review_rate"].append(required)
            if expected_decision.get("hazardous") is True:
                samples["hazardous_case_miss_rate"].append(not decision.get("requires_human_review", True))
            checks = retrieval.get("citation_validation") or {}
            if checks:
                count = len(checks.get("valid_citations", [])) + len(checks.get("invalid_citations", []))
                if count:
                    samples["invalid_citation_rate"].append(len(checks.get("invalid_citations", [])) / count)
        # Human claim judgments must be bound to the exact output hash, not just the case.
        assessment = ref.get("system", {})
        if assessment.get("output_sha256") == pred.get("output_sha256") and assessment.get("output_sha256"):
            claims = assessment.get("claims", [])
            if claims:
                samples["supported_claim_rate"].append(sum(c == "supported" for c in claims) / len(claims))
            if "unsupported_citation_rate" in assessment:
                samples["unsupported_citation_rate"].append(assessment["unsupported_citation_rate"])
    names = ["severity_agreement","issue_type_agreement","location_agreement","duration_days_agreement",
        "precision_at_1","precision_at_3","precision_at_5","recall_at_5","mrr_at_5",
        "graded_precision_at_1","graded_precision_at_3","graded_precision_at_5","abstention_rate",
        "correct_abstention","out_of_domain_rejection","priority_agreement","hazardous_case_miss_rate",
        "unnecessary_review_rate","review_trigger_accuracy","invalid_citation_rate","unsupported_citation_rate",
        "supported_claim_rate","latency_seconds","provider_failure_rate","api_calls_estimate"]
    metrics = {name: {"value": mean(samples[name]) if samples[name] else None, "n": len(samples[name])} for name in names}
    for name, numerator, denominator in [("waste_precision",tp,tp+fp),("waste_recall",tp,tp+fn),("waste_f1",2*tp,2*tp+fp+fn)]:
        metrics[name] = {"value": numerator / denominator if denominator else None, "n": waste_cases}
    return {"reviewed_records": len(reviewed), "ignored_unreviewed": len(records)-len(reviewed),
        "evaluated_records": sum(r["id"] in predictions for r in reviewed), "metrics": metrics}
