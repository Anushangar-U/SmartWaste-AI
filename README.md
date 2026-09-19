SmartWaste-AI

SmartWaste-AI is a university project for IT3041 Information Retrieval and Web Analytics. It will be developed as a multi-agent AI system that supports waste-management decisions through information retrieval and specialized AI agents.

This repository currently contains the initial project foundation only. AI workflows, APIs, retrieval pipelines, and user-interface functionality will be added in later stages.

Member 4 — Decision Agent, UI, Responsible AI
What's here
agents/decision/
├── __init__.py
├── prompts.py    # system prompt + JSON contract for Agent 3
├── agent.py      # decide(analysis, evidence) -> validated decision dict (uses Groq)
└── rules.py      # deterministic Responsible-AI / validation checks

frontend/
└── app.py        # Streamlit UI — citizen complaint form + hidden staff dashboard

tests/
└── test_rules_no_api.py   # tests rules.py with fake data, no API key/cost needed

requirements-member4.txt
.env.example (GROQ_API_KEY, GROQ_MODEL, BACKEND_URL)
Agent 3 runs on Groq, not Claude

The original plan named Claude for Agent 3, but this project uses Groq's free API (model: llama-3.3-70b-versatile) instead, to avoid a paid dependency. The decide(analysis, evidence) function signature and output shape are unchanged, so this doesn't affect how the backend calls it — just worth mentioning in the viva if it comes up.

Get a free key at https://console.groq.com/keys and put it in .env as GROQ_API_KEY. Never commit .env — only .env.example.

The frontend has two modes
Citizen view (default): the complaint form everyone sees.
Staff view: reached only via the small 🔒 icon in the top-right corner — shows a login form, then a priority-sorted complaints queue. Deliberately not a visible tab, so it doesn't compete with the public form.
Backend contract needed for staff login (for Member 3)
POST /auth/login
body: {"username": "...", "password": "..."}
success (200): {"access_token": "..."}   (or {"token": "..."})
failure: any non-2xx status

The frontend doesn't yet attach the token to any other request, since the complaints queue is still stored in Streamlit's own session memory (no shared database wired up yet). Once a real GET /complaints / PATCH /complaints/{id} endpoint exists, those calls should send headers={"Authorization": f"Bearer {token}"}.

Running it yourself
bash
pip install -r requirements-member4.txt
python -m streamlit run frontend/app.py

The UI expects a backend at POST {BACKEND_URL}/complaints and POST {BACKEND_URL}/auth/login (see contract above) — point BACKEND_URL in .env at wherever the real backend ends up running.

Testing the Responsible AI rules without any API key
bash
python tests/test_rules_no_api.py

Confirms priority validation, fabricated-citation stripping, and the human-review triggers (low confidence, missing evidence, hazardous keywords) all work — no cost, no key needed, and unaffected by whether GROQ_API_KEY is real or a placeholder.

Contract relied on from Agents 1 & 2

decide(analysis, evidence) expects:

analysis: dict (waste_types, location, duration_days, severity, issue_type, summary)
evidence: list of {"source": str, "snippet": str}

Flag this with Members 1–3 early so field names don't drift.

Still to build
Wire decide() into the real /agents/decide endpoint once Member 3's backend exists.
Real JWT auth on the backend to replace the placeholder /auth/login contract.
Persist complaints in the shared database instead of Streamlit session memory, so the staff dashboard survives a refresh and works across users.