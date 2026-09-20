"""
SmartWaste AI - Streamlit frontend (v5).

Single page that switches between two modes:
  - "citizen" (default) — the public complaint form. This is what anyone
    landing on the site sees first.
  - "staff"   — reached only by clicking the small 🔒 icon in the top-right
    corner. Shows a login form, then (once "logged in") the priority-sorted
    complaints queue.

This keeps the staff area out of the way visually — it's not a tab
competing for attention next to the citizen form, it's a deliberate,
secondary action tucked in the corner, closer to how real products hide
admin/staff entry points (e.g. a small "Staff login" link in a footer).

=====================================================================
CONTRACT FOR MEMBER 3 (backend/auth) — unchanged from before
=====================================================================
    POST {BACKEND_URL}/auth/login
    form body: username=...&password=...
    success (200): {"access_token": "...", "role": "admin"}
    failure: any non-2xx status.
=====================================================================

Run with:  streamlit run frontend/app.py   (or: python -m streamlit run frontend/app.py)
Configure the backend URL via the BACKEND_URL env var (see .env.example).
"""

import os
import random
import string
from datetime import datetime

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

PRIORITY_STYLE = {
    "critical": {"color": "#7f1d1d", "bg": "#fee2e2", "emoji": "🔴", "rank": 0},
    "high": {"color": "#9a3412", "bg": "#ffedd5", "emoji": "🟠", "rank": 1},
    "medium": {"color": "#854d0e", "bg": "#fef9c3", "emoji": "🟡", "rank": 2},
    "low": {"color": "#166534", "bg": "#dcfce7", "emoji": "🟢", "rank": 3},
}
UNKNOWN_STYLE = {"color": "#374151", "bg": "#f3f4f6", "emoji": "⚪", "rank": 4}

EXAMPLE_COMPLAINTS = {
    "🏫 Near a school": "There has been a pile of mixed organic and plastic waste behind the school for about 5 days now. It's starting to smell.",
    "🏭 Suspected hazardous": "Someone dumped what looks like chemical containers near the riverbank behind the factory.",
    "🏘️ Routine residential": "Our street's bins haven't been collected in 2 days, nothing urgent but it's piling up.",
}

LOCATION_OPTIONS = [
    "Residential street",
    "Near a school",
    "Near a hospital / clinic",
    "Commercial area",
    "Industrial area",
    "Near a water source (river/canal/lake)",
    "Public park",
    "Other",
]


def new_tracking_id() -> str:
    year = datetime.now().year
    suffix = "".join(random.choices(string.digits, k=4))
    return f"WM-{year}-{suffix}"


st.set_page_config(page_title="SmartWaste AI", page_icon="🗑️", layout="wide")

if "complaints" not in st.session_state:
    st.session_state["complaints"] = []
if "auth_token" not in st.session_state:
    st.session_state["auth_token"] = None
if "auth_username" not in st.session_state:
    st.session_state["auth_username"] = None
if "view_mode" not in st.session_state:
    st.session_state["view_mode"] = "citizen"  # or "staff"
if "complaint_text" not in st.session_state:
    st.session_state["complaint_text"] = ""

# ---------- Styling ----------
st.markdown(
    """
    <style>
    .main > div { padding-top: 1.5rem; }
    .swa-hero {
        background: linear-gradient(135deg, #0f766e 0%, #134e4a 100%);
        padding: 1.8rem 2.2rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 1.2rem;
    }
    .swa-hero h1 { margin: 0; font-size: 2.1rem; }
    .swa-hero p { margin: 0.4rem 0 0 0; opacity: 0.9; font-size: 1.02rem; }
    .swa-card {
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 1.4rem 1.6rem;
        background: white;
    }
    .swa-badge {
        display: inline-block;
        padding: 0.35rem 1rem;
        border-radius: 999px;
        font-weight: 700;
        font-size: 1.05rem;
        letter-spacing: 0.02em;
    }
    .swa-tid {
        font-family: monospace;
        background: #f3f4f6;
        padding: 0.15rem 0.5rem;
        border-radius: 6px;
    }
    .swa-row {
        border: 1px solid #e5e7eb;
        border-left-width: 6px;
        border-radius: 10px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.6rem;
        background: white;
    }
    /* Make the corner toggle look like a quiet icon, not a normal button */
    div[data-testid="column"]:has(button[kind="secondary"]) button {
        border: none;
        background: transparent;
        color: #9ca3af;
        font-size: 1.1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Top row: title area + small corner toggle ----------
title_col, corner_col = st.columns([12, 1])
with corner_col:
    if st.session_state["view_mode"] == "citizen":
        if st.button("🔒", help="Staff login", key="to_staff"):
            st.session_state["view_mode"] = "staff"
            st.rerun()
    else:
        if st.button("👤", help="Back to public site", key="to_citizen"):
            st.session_state["view_mode"] = "citizen"
            st.rerun()

# ============================================================
# CITIZEN VIEW
# ============================================================
if st.session_state["view_mode"] == "citizen":
    st.markdown(
        """
        <div class="swa-hero">
            <h1>🗑️ SmartWaste AI</h1>
            <p>Submit a waste-related complaint and get an explainable, evidence-backed priority recommendation.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("ℹ️ How this works (AI pipeline)"):
        st.markdown(
            """
            Your complaint is processed by three specialized AI agents, each with a defined job:
            1. **Analysis** — extracts waste type, location, duration, and severity from your text.
            2. **Knowledge retrieval** — searches internal waste-management guidelines for relevant evidence.
            3. **Decision** — combines the analysis and evidence into a priority and recommendation, explaining its reasoning.

            A final **validation layer** checks the recommendation before you see it — for example,
            flagging cases for human review if evidence is thin or the situation looks high-risk.
            Priority is based only on objective factors (duration, severity, waste type, location risk) —
            never on who is reporting.
            """
        )

    left, right = st.columns([2, 1])

    with right:
        st.markdown("#### Try an example")
        st.caption("Click one to fill the form, then submit.")
        for label, text in EXAMPLE_COMPLAINTS.items():
            if st.button(label, use_container_width=True, key=f"ex_{label}"):
                st.session_state["complaint_text"] = text
                st.rerun()

    with left:
        with st.form("complaint_form"):
            location = st.selectbox("Location type", LOCATION_OPTIONS)
            complaint_text = st.text_area(
                "Describe the waste issue",
                key="complaint_text",
                placeholder=(
                    "e.g. There has been a pile of mixed organic and plastic "
                    "waste behind the school for about 5 days now."
                ),
                height=140,
            )
            submitted = st.form_submit_button("🚀 Submit complaint", use_container_width=True)

        if submitted:
            submitted_complaint = complaint_text.strip()
            if not submitted_complaint:
                st.warning("Please describe the issue before submitting.")
            else:
                request_payload = {"text": submitted_complaint}
                with st.spinner("Analyzing complaint, retrieving evidence, and generating a recommendation..."):
                    try:
                        resp = requests.post(
                            f"{BACKEND_URL}/complaints/process",
                            json=request_payload,
                            timeout=180,
                        )
                        resp.raise_for_status()
                        payload = resp.json()
                        decision = payload.get("decision") or {}
                        result = {
                            **decision,
                            "analysis": payload.get("analysis") or {},
                            "retrieval": payload.get("retrieval") or {},
                            "pipeline_validation": payload.get("validation") or {},
                            "disclaimer": payload.get("disclaimer", ""),
                        }
                    except requests.exceptions.RequestException as exc:
                        st.error(f"Could not reach the backend: {exc}")
                        result = None

                if result:
                    tracking_id = new_tracking_id()
                    priority = (result.get("priority") or "unknown").lower()
                    style = PRIORITY_STYLE.get(priority, UNKNOWN_STYLE)

                    st.session_state["complaints"].append(
                        {
                            "id": tracking_id,
                            "text": submitted_complaint,
                            "location": location,
                            "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            **result,
                        }
                    )

                    st.success(
                        f"✅ Complaint logged as **{tracking_id}**. "
                        "Save this ID to track its status."
                    )

                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown('<div class="swa-card">', unsafe_allow_html=True)

                    badge_col, review_col = st.columns([1, 2])
                    with badge_col:
                        st.markdown(
                            f"""<span class="swa-badge" style="background:{style['bg']}; color:{style['color']};">
                            {style['emoji']} {priority.upper()}</span>""",
                            unsafe_allow_html=True,
                        )
                    with review_col:
                        if result.get("requires_human_review"):
                            st.warning("⚠️ Flagged for human review before any action is taken.")

                    st.markdown("&nbsp;", unsafe_allow_html=True)
                    st.markdown("**Recommended action**")
                    st.write(result.get("recommended_action", "—"))

                    st.markdown("**Explanation**")
                    st.write(result.get("explanation", "—"))

                    analysis = result.get("analysis") or {}
                    retrieval = result.get("retrieval") or {}
                    with st.expander("🔎 Analysis and retrieved knowledge"):
                        st.markdown("**Waste analysis**")
                        st.write(
                            "Waste types: "
                            + ", ".join(analysis.get("waste_types") or ["unknown"])
                        )
                        st.write(f"Location: {analysis.get('location', 'unknown')}")
                        st.write(
                            f"Duration: {analysis.get('duration_days', 'unknown')} days"
                        )
                        st.write(f"Severity: {analysis.get('severity', 'unknown')}")
                        st.write(f"Issue type: {analysis.get('issue_type', 'unknown')}")
                        st.write(f"Summary: {analysis.get('summary', '—')}")

                        st.markdown("**Knowledge retrieval**")
                        st.write(f"Query: {retrieval.get('query', '—')}")
                        st.write(retrieval.get("answer", "—"))
                        st.caption(
                            "Grounded answer: "
                            + ("yes" if retrieval.get("grounded") else "no")
                        )

                    sources = result.get("supporting_sources") or []
                    if sources:
                        st.markdown("**Supporting sources**")
                        retrieved_sources = (
                            result.get("retrieval", {}).get("sources", [])
                        )
                        cited_references = [
                            item
                            for item in retrieved_sources
                            if item.get("source") in sources
                        ]
                        if cited_references:
                            for item in cited_references:
                                st.markdown(
                                    f"- {item.get('source')} "
                                    f"(page {item.get('page', 'unknown')})"
                                )
                        else:
                            for source in sources:
                                st.markdown(f"- {source}")

                    confidence = result.get("confidence")
                    if confidence is not None:
                        st.markdown("**Model confidence**")
                        st.progress(min(max(confidence, 0.0), 1.0))
                        st.caption(f"{confidence:.0%}")

                    st.markdown("</div>", unsafe_allow_html=True)

                    agent_validation = result.get("validation") or {}
                    pipeline_validation = result.get("pipeline_validation") or {}
                    validation_notes = [
                        *agent_validation.get("issues", []),
                        *pipeline_validation.get("warnings", []),
                    ]
                    if validation_notes:
                        with st.expander("🔧 Validation notes (for reviewers)"):
                            for issue in validation_notes:
                                st.markdown(f"- {issue}")

                    st.caption(
                        "This recommendation was generated by an AI system and is "
                        "intended as decision support only. Final action requires "
                        "authorized human sign-off."
                    )

# ============================================================
# STAFF VIEW (reached only via the corner 🔒 button)
# ============================================================
else:
    if not st.session_state["auth_token"]:
        st.markdown("### 🔒 Staff login")
        st.caption("This area is restricted to authorized waste-management staff.")
        with st.form("staff_login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_submitted = st.form_submit_button("Log in")

        if login_submitted:
            if not username or not password:
                st.warning("Enter both a username and password.")
            else:
                try:
                    resp = requests.post(
                        f"{BACKEND_URL}/auth/login",
                        data={"username": username, "password": password},
                        timeout=15,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        token = data.get("access_token") or data.get("token")
                        role = data.get("role")
                        if token and role in {"admin", "staff"}:
                            st.session_state["auth_token"] = token
                            st.session_state["auth_username"] = username
                            st.rerun()
                        elif token:
                            st.error("This account is not authorized for the staff area.")
                        else:
                            st.error(
                                "Login endpoint returned 200 but no "
                                "access_token/token field — check the backend contract."
                            )
                    else:
                        st.error("Invalid username or password.")
                except requests.exceptions.RequestException as exc:
                    st.error(f"Could not reach the backend: {exc}")
    else:
        top_col, logout_col = st.columns([4, 1])
        with top_col:
            st.markdown(f"### 📋 Complaints queue — logged in as `{st.session_state['auth_username']}`")
            st.caption(
                "Sorted by priority. In a full deployment this would read from "
                "the shared database instead of browser session memory."
            )
        with logout_col:
            if st.button("Log out", use_container_width=True):
                st.session_state["auth_token"] = None
                st.session_state["auth_username"] = None
                st.rerun()

        complaints = st.session_state["complaints"]
        if not complaints:
            st.info("No complaints submitted yet in this session.")
        else:
            sorted_complaints = sorted(
                complaints,
                key=lambda c: PRIORITY_STYLE.get((c.get("priority") or "").lower(), UNKNOWN_STYLE)["rank"],
            )
            for c in sorted_complaints:
                priority = (c.get("priority") or "unknown").lower()
                style = PRIORITY_STYLE.get(priority, UNKNOWN_STYLE)
                review_tag = " · 🚩 needs human review" if c.get("requires_human_review") else ""
                st.markdown(
                    f"""
                    <div class="swa-row" style="border-left-color:{style['color']};">
                        <span class="swa-badge" style="background:{style['bg']}; color:{style['color']}; font-size:0.85rem;">
                            {style['emoji']} {priority.upper()}
                        </span>
                        &nbsp; <span class="swa-tid">{c['id']}</span>
                        &nbsp; <span style="color:#6b7280; font-size:0.85rem;">{c['submitted_at']} · {c['location']}{review_tag}</span>
                        <div style="margin-top:0.4rem;">{c['text']}</div>
                        <div style="margin-top:0.4rem; font-size:0.92rem; color:#374151;">
                            <strong>Action:</strong> {c.get('recommended_action', '—')}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
