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
