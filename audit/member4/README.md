# Member 4 / Student 4: IR security audit

IT3041 Individual AI Security Audit and Vulnerability Assessment. This is an evidence-backed assessment of SmartWaste AI, not a mitigation branch.

- Audited production commit: `2a8615c2b24b5c75ab024de8af4525e2f428f165`.
- Audit branch: `audit/member4-ir-security`.
- Date: 27 September 2026. Machine-readable timestamps are UTC.
- Scope: Retrieval Accuracy; Retrieval Manipulation; Hallucination due to Retrieval; Source Reliability; Authentication; Authorization; API Security; Communication Protocol Security.
- Production files, prompts, configuration, PDFs and the real vector store were not edited. Fixture substitutions are confined to audit processes and explicitly labelled.

Start with [results](results.md), [test cases](test_cases.md) and the [risk register](risk_register.md). Use [report outline](report_outline.md) to prepare the assignment and [viva notes](viva_notes.md) to explain the evidence. Personal reflections and manual screenshots remain the student's work.

## Evidence limits

The configured Agent 1 and Agent 2 OpenRouter clients each received HTTP 401. No successful live Agent 1 output or live generated Agent 2 answer was obtained. Subsequent ranking tests used explicitly recorded audit-authored structured inputs plus the actual MiniLM model, FAISS index and PDFs. The raw complaint was also queried directly to isolate retrieval effects from those fixtures. No provider was replaced to conceal this limitation.

24 cases were designed: 22 were dynamically executed at least in part, one is a static-only observation, and one live claim-support case could not execute. Conclusions: 11 PASS, 11 PARTIAL (including static/incomplete cases), 2 FAIL. These are case outcomes, not vulnerability counts. Four technical findings are documented: two Medium and two Low. No live hallucination, authentication bypass or unauthorized data access was demonstrated.

## Reproduction

Run from the repository root with the existing virtual environment. `baseline.py` checks that production still matches the audited commit. Scripts must not be used to assess a changed production version under this report's SHA.

```powershell
.\.venv\Scripts\python.exe -B audit/member4/scripts/baseline.py
.\.venv\Scripts\python.exe -B audit/member4/scripts/retrieval_audit.py
.\.venv\Scripts\python.exe -B audit/member4/scripts/api_audit.py
.\.venv\Scripts\python.exe -B audit/member4/scripts/control_audit.py
.\.venv\Scripts\python.exe -B audit/member4/scripts/pdf_evidence.py
.\.venv\Scripts\python.exe -B audit/member4/scripts/local_supplement.py
.\.venv\Scripts\python.exe -B audit/member4/scripts/final_checks.py
```

The retrieval and API scripts can make external calls using local configuration. They limit the audited SDK requests to 60 seconds with zero automatic retries. Do not rerun these merely to obtain more favourable results. A rerun overwrites same-named evidence; preserve earlier evidence before a separately dated assessment. `HF_HUB_OFFLINE=1` uses the existing model cache. The scripts never rebuild the real FAISS store.

All generated evidence is sanitized before writing. Credentials and temporary authentication tokens remain in memory. The root ignore pattern `logs/` also matches this audit's log directory; only reviewed files in `audit/member4/evidence/logs/` were explicitly added to Git. Do not force-add application logs or `.env`.

## Evidence map

| Material | Location |
|---|---|
| Environment, baseline and corpus fingerprints | `evidence/json/environment.json`, `baseline-tests.json`, `vector-store.json` |
| Baseline command output | `evidence/logs/baseline-tests.txt` |
| Actual rankings and labelled analysis inputs | `evidence/json/IR-01-retrieval.json` through `IR-07-retrieval.json`, `IR-11-retrieval.json` |
| Comparison rankings | `evidence/json/ranking-comparison.json` |
| Threshold prompt/output/downstream capture | `evidence/json/IR-08-threshold.json` |
| PDF passage checks | `evidence/json/IR-10-pdf-verification.json`, `evidence/logs/PDF-*.png` |
| HTTP authentication and validation | `evidence/json/IR-12-*.json` through `IR-16-*.json` |
| Remaining regression and boundary checks | `evidence/json/IR-17-*.json` through `IR-24-*.json` |
| Missing live claim evidence | `evidence/IR-09-claim-check.md`, `evidence/IR-11-support-check.md` |
| Required manual screenshots | `evidence/screenshot-checklist.md` |
| Final integrity and secret checks | `evidence/json/final-integrity.json` |

No mitigations were implemented. Do not merge this audit branch into `main` as part of this task.

Final checks compared all 56 tracked production files and three real vector-store files with their pre-audit SHA-256 fingerprints: unchanged. The audit text scan found no configured credential values or JWT-shaped tokens. All 24 case records have the required eight fields and their referenced evidence files exist. See `evidence/json/final-integrity.json` for the artifact manifest and exact checks; these checks do not claim to be a universal secret detector.
