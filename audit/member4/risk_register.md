# Risk register

These ratings apply to the tested local decision-support system at `2a8615c2b24b5c75ab024de8af4525e2f428f165`. They were assigned after reviewing the audit evidence, not copied from an earlier development review. Four confirmed technical weaknesses are grouped by root cause; no Critical or High finding is claimed.

| Vulnerability ID | Vulnerability | Related Tests | Impact | Likelihood | Severity | Technical justification | Recommended mitigation (not implemented) |
|---|---|---|---|---|---|---|---|
| M4-V01 | Relevance-poor passages qualify as grounding context | IR-01, IR-02, IR-05, IR-06, IR-07 | Moderate: irrelevant evidence may distort advice or explanations | Medium: reproducible on selected ordinary/negated inputs; broader rate unmeasured | Medium | Character chunks include contents/references; cosine threshold measures similarity, not task relevance or negation | Evaluate a labelled retrieval set; remove non-guidance chunks, improve query normalization and assess reranking/metadata filters |
| M4-V02 | Grounded flag does not verify factual support | IR-24; IR-09 limitation | Moderate: unsupported claims can appear grounded | Medium, conditional on unsupported provider output; its natural frequency is unknown | Medium | Real function accepted deliberately unsupported provider fixture with grounded true | Separate evidence availability from verified support; validate citations and claim entailment; abstain/review when unsupported |
| M4-V03 | Negated hazards trigger a hazardous-keyword review | IR-06, IR-17 | Low: unnecessary review, reduced review-signal precision | High for explicit tested negations; prevalence not measured | Low | Substring matching ignores whether hazard terms are negated | Add carefully evaluated negation handling while retaining conservative escalation for real/ambiguous hazards |
| M4-V04 | Source filenames misidentify document titles | IR-10, IR-11 | Low: inaccurate provenance and policy/plan confusion | High: four of five corpus filenames demonstrably mismatch document identity | Low | Source metadata/citations use filename without authoritative title/version fields | Maintain a verified document manifest with title, issuer, year and hash; relabel/rebuild only in a later authorized development task |

## M4-V01: Relevance-poor passages qualify as grounding context

**Description:** The production retriever and filter accepted contents/reference passages and subject-mismatched material. The routine structured query retained `beyond_age_of_waste_p90_c02` (references) and `beyond_age_of_waste_p7_c04` (contents), both above 0.52. Negated hazardous wording yielded five healthcare-guide matches. Not every healthcare passage is wholly irrelevant to municipal waste; the finding is supported particularly by the non-substantive passages and explicit-negation behaviour.

**Evidence:** `evidence/json/IR-01-retrieval.json`, `IR-06-retrieval.json`, `ranking-comparison.json`, and `IR-10-pdf-verification.json`.

**Technical root cause:** Page/character chunking does not exclude contents/references; MiniLM similarity and a fixed 0.35 gate do not establish task relevance. The corpus includes many healthcare passages. That distribution is a possible contributor, not a separately proven causal defect. Query construction can also repeat context; the audit did not isolate each factor experimentally.

**Impact + Likelihood -> Severity:** Moderate information-integrity impact plus reproducible, readily accessible input conditions supports Medium. No live model advice or real-world harm was observed, and human review limits immediate operational impact. Ranking changes from stuffing alone do not prove an exploit; those are supporting sensitivity observations.

**Recommended mitigation:** Curate and label a representative retrieval benchmark, distinguish direct/partial/irrelevant guidance, remove non-guidance text, assess metadata filtering and reranking, and tune thresholds using measured results. Do not simply increase 0.35 without evaluating recall. None implemented.

## M4-V02: Grounded flag does not verify factual support

**Description:** A provider fixture claimed an invented exact 17-hour requirement under a deliberately fictional rule while citing real passage [1]. The real generate_answer function returned that text with grounded true. The cited PDF page did not support the claim.

**Evidence:** `evidence/json/IR-24-grounding-boundary.json`, `evidence/IR-09-claim-check.md`, and `evidence/logs/PDF-who_un_environment_guidance-p153.png`.

**Technical root cause:** In `agents/knowledge_agent/rag_agent.py:253`, a nonempty answer after evidence availability leads to grounded true. The prompt requests support but the response path does not validate citation-to-claim entailment. Filename membership checks in Agent 3 address a different property.

**Impact + Likelihood -> Severity:** Moderate risk of misleading evidence-backed presentation plus conditional Medium likelihood supports Medium. The acceptance behaviour is confirmed, but live hallucination frequency is unmeasured because provider access failed. The fixture is not represented as an actual model-generated hallucination. Authorized human review and decision-support disclaimers reduce the case for a higher rating.

**Recommended mitigation:** Name the evidence-availability flag accurately; enforce valid citation references and check factual support, especially numeric/legal claims; return uncertainty and require review when support is unresolved. No mitigation was implemented.

## M4-V03: Negated hazard keywords force review

**Description:** The sentence explicitly denying chemical, medical, hazardous waste and syringes still received a High-risk keyword detected issue, despite otherwise routine analysis. The requested routine/generated-prose regression passed; this is a separate negation weakness.

**Evidence:** `evidence/json/IR-17-review-rules.json`, case explicit negation; `evidence/json/IR-06-retrieval.json` supplies related retrieval context.

**Technical root cause:** `agents/decision/rules.py:139` uses `any(keyword in text_to_scan ...)`. It identifies lexical presence without parsing negation. Original complaint access makes the rule independent of whether Agent 1 correctly normalizes the denial.

**Impact + Likelihood -> Severity:** Low workflow impact plus high reproducibility for the specific input supports Low. The observed effect is additional review; the test did not raise priority, dispatch a crew, or bypass safeguards. Widespread alert fatigue is a possible downstream consequence, not a measured outcome.

**Recommended mitigation:** Add evaluated negation-aware handling that distinguishes explicit denial from uncertainty, while retaining conservative human review when ambiguity remains. No change was made.

## M4-V04: Misidentified corpus documents

**Description and evidence:** Actual PDF first pages in `evidence/json/IR-10-pdf-verification.json` establish these mappings:

| Stored filename | Actual title |
|---|---|
| `sri_lanka_waste_policy.pdf` | National Action Plan on Plastic Waste Management 2021-2030 |
| `sri_lanka_plastic_action_plan.pdf` | National Policy on Waste Management (2020) |
| `safe_healthcare_waste.pdf` | Compendium of WHO and other UN guidance on health and environment, 2022 update |
| `who_un_environment_guidance.pdf` | Safe management of wastes from health-care activities, second edition (2014) |

**Technical root cause:** Ingestion uses the filename as `source` and the downstream citation path retains it. No title/issuer/version manifest corrects that label. This is mislabelling of the supplied corpus, not demonstrated unauthorized source replacement.

**Impact + Likelihood -> Severity:** Low attribution/interpretation impact plus high observed likelihood supports Low. Reviewers can still open the correct file/page, and all 48 sampled passages matched. Confusing a general policy with a plastic action plan can nevertheless undermine interpretation of legal authority.

**Recommended mitigation:** Verify corpus identities, store official titles/issuers/dates/hashes, and present those with stable source IDs. Renaming/rebuilding is a future mitigation, not part of this audit.

## Informational observations, not additional confirmed exploits

| ID | Related tests | Observation and limitation | Severity | Recommendation |
|---|---|---|---|---|
| M4-O01 | IR-16 | Local HTTP carries frontend/backend traffic; provider URLs are HTTPS. No untrusted-network deployment or interception was tested. | Informational | Use TLS before exposure beyond trusted localhost; verify proxy and credential transport in deployment. |
| M4-O02 | IR-16 | Ten spaces produce 502 after Agent 1 rejects blank input; no provider call or secret leak. | Informational | Normalize/reject blank text at the request boundary in a later change. |
| M4-O03 | IR-23 | No application limiter found; external proxy limits and actual resource exhaustion untested. | Informational | Establish request/cost budgets and deployment limits; validate them through authorized bounded testing. |
| M4-O04 | IR-18 | Parse-failure fallback can show decision.validation.passed true, while review remains true and confidence zero. Final validator checks low confidence. | Informational | Clarify validation semantics and record parse failure explicitly in a later change. |
| M4-O05 | IR-21 / environment | Existing vector store lacks build_info.json; generation history/model revision cannot be independently attested. Actual count/type/dimension and sampled PDF text matched expectations. | Informational | Preserve build provenance when next rebuilding the corpus under development authorization. |

## Successful Security Controls

Threshold enforcement and no-evidence abstention (IR-04/08); protected-route JWT checks (IR-13/15); role authorization (IR-14); intended public access (IR-12); routine/generated-prose separation and actual hazard review (IR-17); invented-source removal and safe malformed-output handling (IR-18); HTML escaping (IR-20); variable-count/missing/mismatched FAISS validation (IR-21); generic provider-error responses (IR-22). These passing controls constrain the findings and their severities.
