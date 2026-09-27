# Manual screenshot checklist

No application/browser screenshots are claimed in this audit. The PDF PNGs already present are rendered source pages. Capture the following only when you personally perform the actions; redact tokens, passwords, keys and unrelated windows.

| Screenshot ID | Related Test ID | Screen/page to open | Exact action to perform | What must be visible | Why it matters |
|---|---|---|---|---|---|
| SS-01 | Baseline / all | Terminal in repository | Show `git show -s --format=%H 2a8615c` and the sanitized baseline log | Full audited SHA and test summaries; no environment variables | Establishes evaluated version and independent baseline run |
| SS-02 | IR-01, IR-05, IR-06 | Editor JSON viewer | Open ranking-comparison.json and corresponding retrieval JSON side by side | Query, ranks, chunk IDs, scores and source/page; label analysis as fixture | Shows actual real-index ranking changes without implying live generation |
| SS-03 | IR-08 | Editor JSON viewer | Open IR-08-threshold.json | Input 0.34/0.35/0.36, retained output and generation/downstream prompt | Demonstrates inclusive filtering and evidence consistency |
| SS-04 | IR-10 | PDF viewer and editor | Open sri_lanka_waste_policy.pdf page 1 beside sri_lanka_plastic_action_plan.pdf page 1 | Filename bar and actual title on each page | Makes the source identity mismatch visible |
| SS-05 | IR-10 | PDF viewer and editor | Open who_un_environment_guidance.pdf PDF page 153 beside its recorded chunk | PDF page indicator, passage and matching source/chunk metadata | Distinguishes accurate page traceability from source-title accuracy |
| SS-06 | IR-13, IR-14, IR-15 | Editor JSON viewer or local test terminal | Show sanitized stored responses, or rerun the audit script only with authorization | 401 for absent/invalid auth, 403 for normal-user access; token value must be redacted | Demonstrates successful auth boundaries |
| SS-07 | IR-16 | Editor JSON viewer | Open IR-16-invalid-input.json | Eight 422 statuses and whitespace-only 502 with generic response | Shows the validation edge case without exaggerating it |
| SS-08 | IR-20 | Streamlit or AppTest evidence viewer | Inspect IR-20-rendering.json; if visually rerunning, use only the synthetic audit fixture | Literal escaped markup displayed as text and the matching evidence record | Complements server-markup verification; do not claim browser testing from JSON alone |
| SS-09 | IR-09, IR-11, IR-19 | Editor JSON viewer | Open IR-01-retrieval.json and IR-19-location.json | HTTP 401 limitation and captured location input; no keys | Documents exactly why live follow-through is incomplete |
| SS-10 | IR-24 | Editor/PDF viewer | Open IR-24-grounding-boundary.json beside PDF page 153 | The prominent fixture label, grounded true, unsupported fictional rule and actual passage | Shows a boundary-control result, not a live hallucination |
| SS-11 | Final integrity | Terminal/editor | Show `git status`, audit commit, and final-integrity.json | Clean branch, unchanged production/store checks, audit-only changed paths | Confirms the assessment did not implement mitigations |

If provider access is later repaired, create a separately dated live follow-up for IR-09/11/19. Do not replace this run's 401 evidence or describe future screenshots as already captured.
