# Civic UI redesign

Base: `500e08029a3c20cd289680e5ca2987217340c9bc` on
`improvement/assignment-completion`. UI branch: `improvement/frontend-ui-ux`.
The latest refinement started from the clean existing UI branch at
`bf0db7f9aa32b46e0abf1b9e00faf33dbbdc9b83`; its original redesign commits were retained.

## Before and after

| Journey | Before | After |
|---|---|---|
| Citizen entry | Workspace sidebar and a long report/tracking page | Public landing page with Report an Issue, Track Complaint and secondary Staff Login |
| Submission | Flat widget list and transient receipt | Three labelled form sections, privacy guidance and a receipt retained in the current session |
| Tracking | Beneath the full report form; raw history table | Separate screen with plain-language status and actual chronological updates |
| Staff entry | Sidebar workspace selector | Dedicated sign-in screen; authenticated header with Citizen Portal and Logout |
| Operations | Dashboard, queue and full case on one page | Dashboard, Complaints, Needs Review, Assigned and Resolved navigation |
| Case review | Raw analysis JSON and long mixed action page | Overview, AI Analysis, Evidence, Recommendation, Human Decision and History tabs |

Preserved: public submission, location/area/clarification, backend tracking, shared queue,
filters, persistent dashboard, analysis/evidence/recommendation, approve/override,
assignment/resolution, failed processing retry, duplicate links and logout.

The API, agents, prompts, model settings, persistence schema and backend authorization
are unchanged. No maps, photos, citizen accounts or notifications were added.

## Design decisions

- Emerald accent `#059669`, neutral background `#fafaf9`, white surfaces, text `#1c1917`,
  muted token `#78716c` and borders `#e7e5e4`. Action green `#047857` and metadata
  `#57534e` provide stronger contrast. Cards use 12–16px radii and a compact hero.
- A native Streamlit light theme keeps inputs, menus, alerts and form-submit buttons
  consistent with the civic palette. Start Streamlit from the repository root so it
  reads `.streamlit/config.toml`.
- The public experience says what residents can do before describing the AI assistance.
- Status labels and urgency text accompany color; color is never the only signal.
- Native labelled widgets retain keyboard behavior. Main action buttons are at least 46 pixels high,
  focus outlines remain visible, and no motion is needed to use the application.
- Form and case cards stack at narrow widths. Queue cards avoid a wide operational table.
- Official source titles, issuer/year, page, exact passage and semantic similarity appear
  together. Raw filenames live in source-detail expanders.
- Model confidence is explicitly uncalibrated. Human decisions have their own tab.
- Evidence availability, grounding and claim verification display separate backend values;
  absent flags say "Not recorded". Recommendation review requirements and cited document
  titles are explicit. Grounding is not presented as independent claim verification.
- Review and resolution require explicit confirmation; assignment is a deliberate form action.
- Case updates use the version the staff form was originally shown with. A conflict is
  shown in plain language; Refresh Case clears old action inputs before adopting a new version.
- Synthetic processing is visibly labelled. There is no fabricated stage progress or statistic.

### Inspiration

The public entry points and separate operational tools take inspiration from
[FixMyStreet's reporting journey](https://fixmystreet.org/how-it-works/) and
[SeeClickFix's issue-reporting flow](https://www.civicplus.help/seeclickfix/docs/report-an-issue-to-my-city).
No branding, assets or CSS were copied. SmartWaste retains its own guest-reporting contract;
it does not claim to reproduce those services' identity or publication policies.

## Frontend boundaries and security

- `frontend/app.py`: public screens, sign-in, navigation and existing HTTP API adapter.
- `frontend/staff.py`: staff presentation and actions over the injected API adapter.
- `frontend/components.py`: reusable badges, timelines, evidence cards and field display.
- `frontend/styles.py`: static CSS only; no external font or JavaScript dependency.
- `frontend/theme.py`: presentation color tokens.
- `.streamlit/config.toml`: native widget theme only; contains no credentials.
- Dynamic HTML in presentation helpers is escaped. Complaint text, evidence, names,
  notes and recommendations use native plain text. Technical JSON is opt-in.
- Passwords are transient input to the sign-in callback and cleared on success or failure;
  no password copy is retained as application state. Streamlit necessarily handles the
  password widget's transient value. Tokens are never rendered.
- Logout and rejected/expired staff access clear staff session data. Protected requests
  continue to rely on backend role checks.
- Public tracking uses the existing safe response. Internal notes stay in the staff view.

## Local mock demonstration without editing .env

In a dedicated PowerShell terminal, activate the existing environment and run:

```powershell
$env:USE_MOCK_AGENTS = 'true'
$env:DATABASE_PATH = 'data/ui-demo.sqlite3'
python -m uvicorn backend.main:app --no-access-log
```

This uses a separate ignored demo database. Existing configured bootstrap credentials are
used only to initialize an absent account; do not display or put credentials in screenshots.
Close the dedicated terminal afterward to discard these process environment overrides.
Do not run another backend on the same port at the same time.

In another activated terminal:

```powershell
python -m streamlit run frontend/app.py
```

Open `http://localhost:8501`. Use a separate browser or private window for the staff session.

## Best 5-minute UI demo

1. Open Home. Point out **Report an Issue**, **Track Complaint**, **Staff Login** and
   **No account required**. Acknowledge the synthetic demo-mode notice.
2. Click **Report an Issue**. Enter a synthetic uncollected-waste complaint, select a
   location type, optionally enter a public landmark and duration, then **Submit Complaint**.
3. Show **Complaint submitted**, the status and copyable private tracking ID.
4. In the second browser, click **Staff Login**, enter your local staff credentials and **Sign In**.
5. Show dashboard counts, then **Open Complaints** and **Open Case** for the new report.
6. Open **AI Analysis**, **Evidence** and **Recommendation**. Explain synthetic evidence,
   semantic similarity and model-reported confidence honestly.
7. Open **Human Decision**, select approval (or override), enter a reason, confirm review,
   then **Save Human Decision**.
8. Enter a team and click **Assign Complaint**. Enter a resolution note, confirm completion,
   then **Mark Resolved**.
9. In the citizen browser, click **Track this complaint**, then **Check Status**. Show
   **Resolved** and the recorded timeline; staff notes are absent.
10. In the staff browser, click **Logout** to return to the public landing page.

## Screenshots to capture

Use synthetic data and mask tracking capabilities when sharing screenshots.

1. Desktop Home, showing brand, two primary public tasks and Staff Login.
2. Report form with location and optional details.
3. Submission receipt with tracking ID masked.
4. Public tracking after resolution, showing actual status history.
5. Staff login with empty username/password fields.
6. Dashboard populated with your actual stored synthetic reports.
7. Needs Review queue and semantic status badges.
8. Case Evidence tab with source title/page/passage and the verification notice.
9. Human Decision showing approval/override and confirmation.
10. Narrow browser Home and report form, around 390 pixels wide.

## Verification and limits

Latest results: **14 frontend tests passed** in 24.731 seconds; **70 complete deterministic
tests passed** in 33.566 seconds. The original complete baseline had 58 tests; the prior
UI branch had 68. No external provider calls were used.

Commands (from the repository root, in the existing virtual environment):

```powershell
python -B -m unittest tests.test_frontend -v
python -B -m unittest discover -s tests -v
```

The frontend baseline had 2 passing tests. Expanded AppTest coverage exercises public entry,
opt-in login, rejected roles, expired sessions, secret-free error messages, idempotent retries,
tracking and safe complaint rendering. Two independent Streamlit sessions connect to the real
FastAPI application using a temporary database and process-local mock agents. The complete
journey covers submission, dashboard, queue, case tabs, human review, assignment, resolution,
citizen lookup and logout; additional checks cover retry/override, duplicate confirmation,
empty states, filters and stale-version conflicts. New checks cover invalid credentials,
unknown tracking IDs, independent evidence flags, missing metadata and cited source titles.

Actual headless Chrome checks used the real local FastAPI and Streamlit servers with an
isolated temporary database, no complaint records and no seeded staff credentials. Screenshots
were inspected for desktop Home and narrow Home, Report, Track and Login. At 390px the page
and app widths stayed at 390px, with no page exceptions. Main action buttons were 46px high;
select arrows, help and password controls measured at least 44x44px. Native theme configuration
fixed dark default widget styles; mobile top spacing prevents the brand being obscured by
Streamlit's toolbar. The browser helper and temporary servers were stopped after checking.

Local screenshots are ignored Git artifacts in `data/ui-review/`: `home-desktop.png`,
`home-narrow.png`, `report-narrow.png`, `report-fields-narrow.png`, `track-narrow.png` and
`login-narrow.png`. These contain no complaints or entered credentials. Authenticated staff
workflows were checked through AppTest rather than visually in Chrome. Physical mobile,
screen-reader behavior and full accessibility compliance remain unverified. Streamlit's
internal DOM styling may need adjustment after a future Streamlit version upgrade.

Navigation stays in the Streamlit session rather than shareable page URLs. Tracking refresh
is explicit; there is no live stage streaming. The code block's native copy control/selectable
text is used for tracking, with no clipboard JavaScript. Urgency is visible and affects the
backend queue order; an urgency filter was not invented because the API does not expose one.
Live provider health and existing triage limitations were outside this UI-only change.
