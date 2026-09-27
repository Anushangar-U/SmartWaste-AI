# Results of the 27 September 2026 audit

Audited commit: `2a8615c2b24b5c75ab024de8af4525e2f428f165`. Production behaviour was assessed, not repaired. The baseline run independently passed 24 automated tests, plus the manual-output rules smoke script.

## Counts and interpretation

24 audit cases designed; 22 dynamically executed at least in part; 1 static-only case (IR-23); 1 not executed (IR-09). Conclusions across all cases: **11 PASS, 11 PARTIAL, 2 FAIL**. Among dynamic cases: 11 PASS, 9 PARTIAL, 2 FAIL. The not-executed/static cases use PARTIAL to satisfy the assignment's three allowed conclusion values; they are not counted as dynamic executions. Some executed cases also have blocked live substeps.

| Test | Result | What the evidence supports |
|---|---|---|
| IR-01 | PARTIAL | Routine retrieval includes a healthcare-disposal passage and non-guidance material; live analysis/answer blocked |
| IR-02 | PARTIAL | Substantive hazardous guidance found alongside contents and narrower mercury material |
| IR-03 | PARTIAL | Vague input retains broad guidance; actual generated uncertainty handling unavailable |
| IR-04 | PASS | Real scores all below 0.35; grounded false, no evidence or provider call |
| IR-05 | PARTIAL | Keyword stuffing substantially changes real rankings; change alone is not an exploit |
| IR-06 | FAIL | Negated hazards dominate matches and trigger deterministic hazard review |
| IR-07 | PARTIAL | Actual query contains "near beside" and repeated location/duration |
| IR-08 | PASS | Inclusive 0.35 boundary and retained prompt/output/downstream consistency work |
| IR-09 | PARTIAL | Not executed: no live generated answer for claim mapping |
| IR-10 | PARTIAL | 48/48 passages match actual PDF pages; four filename/title mismatches |
| IR-11 | PARTIAL | Corpus search and real retrieval ran; unsupported-fact generation unavailable |
| IR-12 | PASS | Public route intentionally accepts unauthenticated requests; fixture success and sanitized live failure |
| IR-13 | PASS | Three unauthenticated protected routes return 401 |
| IR-14 | PASS | Three admin operations reject a normal-user token with 403 |
| IR-15 | PASS | Invalid, malformed and expired auth return controlled 401 |
| IR-16 | PARTIAL | Eight malformed requests return 422; whitespace returns 502; protocols inspected statically |
| IR-17 | PASS | Generated hazard prose does not flag routine complaint; real hazard words in original complaint require review |
| IR-18 | PASS | Malformed outputs and invented citations require review; fallback validation flag nuance recorded |
| IR-19 | PARTIAL | Selected location reaches real Agent 1 input; provider rejection blocks later stages |
| IR-20 | PASS | Actual Streamlit-generated queue markup escapes dynamic citizen text |
| IR-21 | PASS | Three-vector corpus accepted; missing and inconsistent stores fail explicitly |
| IR-22 | PASS | Simulated provider failures become generic 502 without exception markers |
| IR-23 | PARTIAL | Static-only: no application limiter seen; external deployment not audited |
| IR-24 | FAIL | Unsupported provider fixture receives grounded true without claim verification |

## Findings from retrieval and source inspection

The actual index contains 2,716 vectors: 467 from Beyond an Age of Waste, 707 from the WHO/UN compendium, 149 from the national policy, 167 from the plastic action plan and 1,226 from the healthcare-waste guide. Names in the metadata do not consistently match those document identities; see IR-10.

The routine structured query retained two passages that are visibly references/contents, despite scores above 0.52. It also retrieved healthcare disposal rather than a collection response procedure. This is a relevance weakness, not proof of a harmful generated recommendation. In the negation case, all five matches came from the healthcare guide with scores about 0.575-0.591. Raw-query comparisons independently showed the same healthcare concentration without relying on Agent 1 fixtures.

Keyword stuffing reduced overlap with the routine query to two of five structured matches and one of five raw-query matches. Since appended hazard words can legitimately change the apparent report, this is recorded as sensitivity evidence rather than an independent prompt-injection vulnerability.

All 48 checked chunks existed on the stated PDF pages. Visual review confirmed the two Sri Lankan filenames are swapped relative to their titles. The WHO compendium/healthcare-guide filenames likewise identify each other's subject matter. Page fidelity is successful; the source identity labels are not reliable.

## Successful Security Controls

- **Evidence filtering:** IR-08 shows 0.34 excluded, 0.35/0.36 included, and the same evidence reaching generation and the downstream adapter. IR-04 verifies insufficient evidence on an actual out-of-domain query.
- **Authentication:** IR-13 and IR-15 show controlled 401 for all tested absent/invalid/expired cases, without traceback or credential leakage.
- **Authorization:** IR-14 shows valid normal-user authentication does not grant admin agent access.
- **Public access by design:** IR-12 is consistent with the documented public complaint workflow. It is not classified as an authentication vulnerability.
- **Human-review rules:** IR-17 verifies routine/generated-prose separation and actual original-complaint hazard review. Existing high-severity, critical, low-confidence and non-grounded checks passed the independent baseline suite.
- **Model-output controls:** IR-18 removes fabricated source names and requires review; malformed/incomplete outputs produce review-required results.
- **Rendering:** IR-20 demonstrates HTML escaping in the actual frontend output. It does not claim a browser penetration test.
- **Store validation:** IR-21 accepts a three-vector corpus and rejects missing/mismatched temporary stores.
- **Error handling:** IR-22 wraps provider exceptions in generic service errors without exposing fixture markers.

## Limits and observations

Both configured OpenRouter paths returned 401. This is an environmental limitation, not evidence of successful live hallucination or a vulnerability in project authentication. No real Groq completion was reached by the public pipeline after Agent 1 failed. IR-09 remains incomplete; IR-11 cannot establish how a live answer would handle the legal query. IR-19 confirms input propagation but not successful live downstream use.

The whitespace-only input produced a misleading 502 instead of a client-validation error. Local HTTP, no visible application rate limit, absent historical build metadata and the malformed-fallback validation flag are separately recorded informational observations. There was no load test, traffic interception, remote-deployment audit, credential cracking or corpus tampering.

See [risk register](risk_register.md) for four root-cause findings and bounded severity reasoning. No mitigations were implemented.
