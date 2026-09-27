# Reproducible evaluation

`complaints.template.json` contains 60 generated candidate complaints in 20 families.
Every record is UNREVIEWED and has blank references. `complaints.reviewed.json` starts empty.
The team must review examples against the project triage rubric and actual evidence, fill
reference fields, record reviewer/date, and set REVIEWED before copying them to the reviewed
file. These judgments are reference annotations, not infallible ground truth. Keep related
paraphrases in one split; the starter split is provisional and should be stratified by the
team before experiments. Never tune on held-out cases.

Run from the repository root:

```powershell
python -m evaluation.run_agent1_eval --dataset evaluation/complaints.reviewed.json --live --limit 5
python -m evaluation.run_retrieval_eval --variant baseline
python -m evaluation.run_retrieval_eval --variant deduplicated
python -m evaluation.run_decision_eval --live --limit 5
python -m evaluation.run_system_eval --variant rules
python -m evaluation.run_system_eval --live --limit 5
```

Each runner also accepts `--predictions path.json` (case-ID keyed outputs), `--output DIR`
and `--limit`. Provider runs require live configuration, explicit --live and REVIEWED records.
Retrieval uses the existing local index and raw complaint query to isolate retrieval; it
does not regenerate the index or call Agent 1. Decision-only runs require independently
prepared `input_analysis` and `input_retrieval`, clearly distinct from end-to-end outputs.
Rules baseline is a deliberately simple hazard-keyword comparator, not a replacement agent.
No heavy reranker was adopted because no reviewed benchmark currently establishes a gain.

## Reference format and metric interpretation

- `reference.agent1`: only include fields actually annotated. Explicit duration null means
  the reviewer expects missing duration. Waste metrics are micro precision/recall/F1;
  other extraction fields use exact agreement after the team's consistent labeling.
- `reference.retrieval.relevance`: chunk ID or source filename -> relevant,
  partially_relevant, irrelevant. Strict precision counts relevant only; graded precision
  gives partial matches 0.5. Precision@k divides by k, including when fewer items return.
  All returned positions must be judged before ranking metrics are computed. Set
  relevant_ids_complete=true only when the relevant set is exhaustive; otherwise Recall@5
  remains unavailable. Avoid mixing chunk and source granularity within a case.
- `reference.retrieval.expected_abstain` and `out_of_domain` enable abstention checks.
- `reference.decision`: priority, review_required, hazardous. Hazard miss means failure to
  require review on a reference hazardous case; it is not an estimate of real-world injury.
- `reference.system`: output_sha256 plus claims (supported/partially_supported/unsupported)
  binds human claim review to the exact generated output. Human unsupported_citation_rate
  can be supplied here. Deterministic invalid-citation rate is reported separately; valid
  citation membership does not prove semantic support.

Every metric reports its denominator. Missing labels/outputs are not counted as successes;
failures have a separate rate, and aggregate scores over successful outputs must be read
with coverage/failure counts. No reviewed examples means null metrics, not zero accuracy.
Latency is measured; API call counts are estimates excluding SDK retries. Costs remain
unknown when exact model routing/pricing is unavailable. JSON/CSV/Markdown summaries and
sanitized predictions are written together. Review outputs for personal information before
sharing; use synthetic or consented complaints only.
