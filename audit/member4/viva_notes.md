# Viva preparation - evidence-based explanations

Use these notes to understand and explain the actual system. They are not a script claiming personal experience. The audited version is `2a8615c2b24b5c75ab024de8af4525e2f428f165`; production was not changed.

## Actual implementation in simple terms

| Concept | Meaning in SmartWaste AI |
|---|---|
| RAG | Retrieval-augmented generation: Agent 2 searches the local document collection, then asks an OpenRouter model to answer using retained passages. |
| Semantic search | Search by learned meaning rather than exact word overlap. Similarity is useful but can overreact to hazard terms even when negated. |
| MiniLM | The `all-MiniLM-L6-v2` sentence-transformer used to represent chunks and queries numerically. It is not the answer-generating model. |
| Embeddings | Lists of numbers representing text. Related text can receive similar vectors. They do not store an explicit truth verdict. |
| Embedding dimensions | Each vector has 384 coordinates here. That is a representation size, not a confidence score or number of documents. |
| FAISS | The local vector-search library. It returns nearest stored vectors and their scores; metadata maps them back to text. |
| IndexFlatIP | A flat exact inner-product index. The audit observed this type in the actual saved index. It is not an approximate graph index. |
| Normalized inner product | Vectors are scaled to unit length, then their dot product is computed. For normalized vectors this equals cosine similarity. |
| Cosine similarity | Measures directional similarity. A score above 0.35 is not a 35% probability of correctness. |
| Top-k | Retrieve up to the five best matches before filtering. Fewer than five may remain afterward. |
| Retrieval threshold | Each chunk must score at least 0.35. The exact boundary is inclusive. |
| Evidence filtering | Remove weak individual chunks before building the generation prompt and downstream evidence list. IR-08 confirmed this. |
| Source/page traceability | Each result carries chunk ID, filename, 1-based PDF page, text and score. All 48 sampled passages matched their actual pages, but four filenames misidentified titles. |
| Grounding | Factual claims should follow from evidence. The actual grounded flag checks evidence availability and nonempty output, not full semantic support. |
| Authentication | Establishing identity, here using login and a signed JWT. Absent/invalid/expired tokens returned 401 in the tests. |
| Authorization | Checking what an authenticated identity may do. A normal-user token returned 403 on admin-only agent routes. |
| JWT | A signed token with subject, role and expiry. It is not inherently encryption. Tokens were kept in memory and redacted from evidence. |
| HTTP | Local frontend/backend traffic uses HTTP at localhost. It does not supply transport encryption. The local setting alone is not proof of a remote vulnerability. |
| HTTPS | Provider URLs use HTTPS, which supports encrypted transport and server certificate verification through normal clients. This audit did not perform packet/TLS interception tests. |
| API validation | Pydantic enforces field types and lengths. Eight malformed cases gave 422; ten spaces passed the length check and later caused a controlled 502. |
| Human review | Rules can force staff review for hazards, missing/weak evidence, low confidence and validation issues. This reduces risk; it does not prove the advice itself is correct. |

The actual flow is Streamlit -> public FastAPI route -> orchestrator -> Agent 1 -> Agent 2 query/MiniLM/FAISS/filter/OpenRouter -> Agent 3 Groq/rules -> backend validation -> JSON response -> Streamlit. The original selected location is appended to the analysis input when absent from the text. The live audit observed that appended input, but provider rejection blocked later stages.

## Explaining M4-V01: retrieval relevance weakness

**Why select the test?** Ordinary complaints are the expected application workload; comparing them with stuffing and negation tests whether similar words overwhelm useful context.

**What was expected?** Substantive household collection guidance and recognition that explicitly denied hazards are not affirmative facts.

**What happened?** Routine retrieval retained contents/reference material above 0.52. The negation query returned five healthcare-guide passages. Direct raw-query searches confirmed the concentration independently of Agent 1 fixtures.

**Why technically?** The pipeline indexes character chunks and gates them by cosine similarity. Neither operation verifies passage usefulness or logical negation. Query repetition and corpus composition may contribute, but their individual effect was not isolated.

**Why a vulnerability?** It is an information-integrity weakness: unsuitable evidence is eligible to influence a recommendation. Ranking change alone is not unauthorized access, and no harmful live answer was observed.

**Impact / likelihood / severity:** Moderate possible distortion of advice; Medium estimated likelihood based on reproducible accessible inputs. Medium severity, limited by human review and missing live outcome data.

**Recommended mitigation:** Measure relevance with labelled queries; remove non-guidance chunks; evaluate better filtering/reranking; calibrate the threshold. Do not assert a particular threshold fixes the issue without testing.

**Security / Responsible AI implication:** Evidence-backed presentation must not conceal irrelevant context. Be honest about the limits of a small qualitative sample.

## Explaining M4-V02: unverified grounded status

**Why select the test?** A user may read grounded yes as assurance that claims are supported.

**What was expected?** An unsupported exact legal claim should not automatically gain verified grounding status.

**What happened?** A clearly labelled provider-response fixture invented a 17-hour rule and cited [1]. The actual function returned grounded true. The cited actual PDF page did not support that rule.

**Why technically?** The function accepts any nonempty response after qualifying evidence exists. Prompt instructions are not an enforcement check. A valid citation number or filename is not proof of claim entailment.

**Why a vulnerability?** The application can misrepresent unsupported output as grounded at the tested trust boundary. This was a fixture experiment, not a live model hallucination.

**Impact / likelihood / severity:** Moderate trust/information-integrity impact; conditional Medium likelihood if a provider emits unsupported text, with natural frequency unmeasured. Medium severity, not High, given the decision-support context and lack of demonstrated harmful action.

**Recommended mitigation:** Separate evidence availability from support verification; check citations and claims; abstain or require review when uncertain.

**Security / Responsible AI implication:** Avoid overstating model reliability. In the viva explicitly say that IR-09 live claim verification could not execute because OpenRouter returned 401.

## Explaining M4-V03: negated hazard review

**Why select the test?** People may describe what waste is not present. Safety rules should distinguish those statements from hazard reports.

**What was expected?** Denied hazards would not independently trigger a hazardous-keyword flag.

**What happened?** The original sentence saying not chemical, not medical, not hazardous and no syringes still forced human review.

**Why technically?** The rule uses keyword substrings in complaint/analysis fields, without grammatical negation handling. Moving the scan away from generated prose fixed a different source of false positives.

**Why a vulnerability?** Review precision is reduced. The test showed additional review, not an automatic dangerous action or raised priority.

**Impact / likelihood / severity:** Low workflow impact and high reproducibility for this wording -> Low. Potential review fatigue is not claimed as measured damage.

**Recommended mitigation:** Evaluate negation-aware rules while conservatively retaining review for ambiguous or genuinely hazardous cases.

**Security / Responsible AI implication:** Safety controls must balance false positives and false negatives. Do not weaken real hazard handling merely to make the benign example pass.

## Explaining M4-V04: source identity labels

**Why select the test?** Citations are useful only if a reviewer can identify what document is being cited.

**What was expected?** Filenames and source labels would match document identity and every passage/page would exist.

**What happened?** All 48 passages matched, but four of five filenames mismatched the titles. For example, sri_lanka_waste_policy.pdf is the plastic action plan, while sri_lanka_plastic_action_plan.pdf is the national policy.

**Why technically?** The metadata preserves filenames as source identity without a verified title/issuer/version manifest.

**Why a vulnerability?** Attribution and interpretation of policy authority can be misleading. There is no evidence of unauthorized document substitution or forged passages.

**Impact / likelihood / severity:** Low interpretive impact, high observed prevalence in the current corpus -> Low. Working page traceability limits the harm.

**Recommended mitigation:** Verify document identities and display official titles with stable IDs, dates and hashes in a later development task.

**Security / Responsible AI implication:** Provenance includes accurate identity, not just a source string that exists.

## Important PASS results to explain

- IR-08: 0.34 was excluded and 0.35 included. Prompt, returned evidence and downstream adapter matched. A correct gate can coexist with poor relevance above that gate.
- IR-04: The real laptop-maintenance query produced no qualifying evidence; the system abstained locally without a provider request.
- IR-13/15: 401 demonstrates failed authentication handling. IR-14's 403 demonstrates authorization after successful normal-user authentication. These are different controls.
- IR-12: Public complaint submission is intentional. Calling it an auth vulnerability would ignore the system's intended access policy.
- IR-17: Hazard words in generated prose did not flag the routine complaint, but hazard words in the actual complaint still required review.
- IR-18: Invented source names were removed and review required; malformed results fell back safely. The validation.passed flag on a normalized fallback is a separate informational nuance.
- IR-20: AppTest verified escaped output from the actual frontend. It did not test browser execution or exploit a real staff session.
- IR-21: A valid three-vector corpus passed. Missing/mismatched temporary stores failed explicitly. The real 2,716-vector store was preserved.
- IR-22: Controlled provider failures produced generic API errors without the injected exception markers.

## Evidence and integrity questions

**Did every case run live?** No. Retrieval used the real local model/index/PDFs, APIs used local ASGI, some boundary cases used declared fixtures, and live answer generation was blocked by 401. The counts distinguish these modes.

**Did you find 24 vulnerabilities?** No. There were 24 cases, four grouped technical findings, multiple successful controls and informational observations.

**Did you fix anything?** No production file or configuration was changed. Recommendations are documentation only. Compare the audited baseline with this branch and inspect the final integrity JSON.

**Can you claim Sri Lankan law has no collection deadline?** No. The local corpus search did not establish the requested exact deadline. That is not an exhaustive legal conclusion, and no live answer was available to assess.

**What should be completed personally?** Capture the checklist screenshots, review the evidence, explain your own reasoning, and write your own reflection. Do not claim screenshots or live tests you did not perform.
