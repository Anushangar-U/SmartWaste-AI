# Assignment completion implementation log

Production baseline: `2a8615c2b24b5c75ab024de8af4525e2f428f165`.
Branch: `improvement/assignment-completion`.
Preserved audit branch: `9a1508db84807a81cd23941609876a3147b85672`.

Baseline: 24 deterministic tests passed; the seven manual rules examples completed
(the latter are printed examples, not additional automated assertions).
Architecture before: Streamlit session memory -> FastAPI -> three agents -> validation.
Architecture after: persisted cases surround that same agent pipeline, with authorized
staff actions and safe public tracking. Phase details and verification are recorded below.

## Phase 1
SQLite additive initialization, unique backend tracking identifiers, idempotent submission,
optimistic concurrency for staff actions, safe tracking history and review/assignment/resolution.
Original process route retains its successful response contract and now also saves cases.
New submission returns the tracking record even on provider failure. All case data in tests
uses a temporary database. No real database or generated index is committed.
Verification: 12 workflow/integration tests passed (3 new workflow cases).

## Phase 2
Persistent accounts; bootstrap never resets stored credentials. JWT subjects are looked up
on every protected request: disabled/deleted users are rejected and current roles apply.
Registration always creates normal users. Staff/admin share case operations; agent debug
routes stay admin-only. Lifespan initialization permits fully isolated test databases.
Verification: 7 auth/workflow tests passed, including two independent ASGI clients.

## Phase 3
Streamlit submits persisted cases, retains an idempotency key on retries, looks up safe
tracking history and reads the shared staff queue. Filters, pagination, details,
approve/override, assignment, resolution and retry are connected. Citizen responses omit
private details; dynamic complaint/evidence text uses plain rendering.
Verification: 6 frontend/auth tests passed. AppTest path resolution was corrected before committing.

## Phase 4
Explicit SDK timeouts and bounded retries; stage checkpoints survive failure and retries
resume saved outputs. Active processing cannot be concurrently retried; expired leases can
be recovered after an interrupted process. Total attempts are capped. Readiness reports
safe configuration/file/database checks, not a false guarantee of valid credentials.
Verification: 13 resilience/integration/frontend tests passed. Provider failure messages
are sanitized; no live provider requests were used for this phase.

## Phase 5
Verified five-document title/issuer/year/jurisdiction/hash manifest preserves historical
filenames. Runtime evidence gains official metadata. Queries avoid repeated summary fields;
candidate retrieval remains MiniLM/FAISS with five deduplicated results and threshold 0.35.
Conservative page exclusion is recorded in future build metadata. The existing development
index is not rebuilt by tests. No reranker or unmeasured quality gain is claimed.
Verification: 10 retrieval/build tests passed. Read-only inspection of 741 extractable
pages identified three excluded pages (two contents, one manually inspected reference-only
page), corresponding to 28 chunks. Other uncertain pages remain included. These exclusions
take effect on an explicit rebuild; current generated artifacts were left intact.

## Phase 6
Numbered citations are checked against retained evidence, manifest hashes, actual PDF pages
and passage text. Invalid references are removed and review is required. Legal/quantity
screening is explicitly a conservative heuristic, never an entailment verdict. Legacy
grounded remains a compatibility flag; new metadata/UI distinguish evidence availability,
unverified claims and model-reported (uncalibrated) confidence.
Verification: 24 citation/RAG/decision/integration tests passed, including real PDF passage checks.

## Phase 7
Documented project triage policy separates model collection priority from deterministic
review urgency. Queue sorts urgent review first. Conservative English negation distinguishes
denials, affirmative hazards and uncertainty. Optional pre-submission clarifications are
stored separately from original text; missing facts generate predefined follow-up questions.
Verification: 25 triage/decision/integration/workflow/frontend tests passed. A direct-rule
compatibility regression was resolved before proceeding; existing tests were not weakened.

## Phase 8
60 candidate complaints in 20 paraphrase families, all UNREVIEWED; reviewed file is empty.
Separate extraction/retrieval/decision/system runners support reviewed-label metrics,
saved predictions, bounded opt-in provider runs and simple retrieval/rules baselines.
Claim judgments bind to output hashes. Null metrics and denominators prevent invented scores.
Verification: 3 metric tests passed. Running the system evaluator on all 60 candidates
produced NO_REVIEWED_CASES (0 evaluated) with JSON/CSV/Markdown summaries, not accuracy claims.

## Phase 9
Optional explicit public-area input, bounded recent-area candidate search and cached local
MiniLM similarity suggest duplicates. Generic location types never imply a shared precise
location. Staff confirmation creates a link, not a merge; original cases and statuses remain.
If the local model is absent, suggestions report unavailable without downloading a model.
Verification: 7 duplicate/workflow/frontend tests passed using synthetic similarity fixtures.

## Phase 10
Dashboard aggregates persisted cases by status, priority, area and recorded processing mode,
with backlog and mean/median resolution hours only when at least two completions exist.
No seeded statistics. Historical records without mode metadata are explicitly unknown;
new demo records are labelled separately from live records in public/staff views.
Verification: 7 dashboard/frontend/auth tests passed; statistics tests use temporary fixtures.

## Phase 11
Privacy notice and operator documentation, configurable retention (dry-run by default),
bounded per-address public/auth request windows, bounded pipeline concurrency and body size,
trimmed input validation, and shared correlation IDs. Tracking capabilities are excluded
from application route-template logs. Controls document their single-process/proxy limits.
Verification: 9 resource/auth/resilience tests passed. Retention tests deleted only synthetic
expired resolved cases in temporary databases; no development data was deleted.

## Phase 12
Provider configuration uses the existing settings layer; operational settings have bounded
values. Direct dependency versions record the actually installed Python 3.13 environment.
CI runs deterministic tests and evaluation smoke checks offline without provider secrets or
a generated FAISS index. README documents setup, migrations, API, evaluation and demo steps.
Separate interpreter tests verify persisted records survive process restart.
Verification: full suite passed 57 tests, followed by 6 focused restart/migration/workflow
checks after adding a legacy-schema migration regression. pip check reported no broken
requirements. All four evaluation entry points reported no reviewed cases without live calls.
Final acceptance review also removed validation-error input echoes, preserved urgent review
on analyst failure, and prevented mixing saved mock/live outputs during retry.
