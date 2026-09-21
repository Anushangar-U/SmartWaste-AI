"""
SmartWaste AI - Streamlit frontend (v7).

WHAT CHANGED FROM v6, AND WHY:

1. BUG FIX — tracking IDs "disappearing": in v6, complaints only lived in
   st.session_state, which is tied to one browser session. Reloading the
   page, or Streamlit restarting the session for any reason, wiped it —
   that's why the ID became untrackable after you switched to staff and
   back. Fixed with simple JSON-file persistence (see PersistentStore
   below): every complaint is saved to a local file on disk immediately,
   and reloaded from disk on startup, so it survives refreshes/restarts.
   This is a stand-in for the real shared database mentioned in your tech
   stack — swap PersistentStore for real DB calls once that exists.

2. NAVIGATION — replaced the manual tabs + hidden corner-icon hack with
   Streamlit's actual built-in multipage navigation (st.Page +
   st.navigation), which renders a real sidebar menu with icons. This is
   the standard, polished way to structure a Streamlit app — not a custom
   CSS workaround.

Run with:  streamlit run frontend/app.py   (or: python -m streamlit run frontend/app.py)
Configure the backend URL via the BACKEND_URL env var (see .env.example).

=====================================================================
CONTRACT FOR MEMBER 3 (backend/auth) — unchanged
=====================================================================
    POST {BACKEND_URL}/auth/login
    body: {"username": "...", "password": "..."}
    success (200): {"access_token": "..."} or {"token": "..."}
    failure: any non-2xx status.
=====================================================================
"""

import json
import os
import random
import string
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Local-only persistence file. This is a stand-in for the real shared
# database — fine for a demo/dev machine, not meant for production.
STORE_PATH = Path(__file__).parent / ".local_complaints_store.json"

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


# ---------- Persistence ----------
def load_complaints() -> list:
    if STORE_PATH.exists():
        try:
            return json.loads(STORE_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            return []
    return []


def save_complaints(complaints: list) -> None:
    try:
        STORE_PATH.write_text(json.dumps(complaints, indent=2))
    except OSError:
        pass  # best-effort local persistence; not critical if it fails


def new_tracking_id() -> str:
    year = datetime.now().year
    suffix = "".join(random.choices(string.digits, k=4))
    return f"WM-{year}-{suffix}"


def find_complaint(tracking_id: str):
    for c in st.session_state["complaints"]:
        if c["id"].strip().upper() == tracking_id.strip().upper():
            return c
    return None


def inject_styles():
    st.markdown(
        """
        <style>
        .main > div { padding-top: 1.5rem; }
        .swa-hero {
            background: linear-gradient(135deg, #0f766e 0%, #134e4a 100%);
            padding: 1.6rem 2rem;
            border-radius: 16px;
            color: white;
            margin-bottom: 1.2rem;
        }
        .swa-hero h1 { margin: 0; font-size: 1.8rem; }
        .swa-hero p { margin: 0.4rem 0 0 0; opacity: 0.9; font-size: 1rem; }
        .swa-badge {
            display: inline-block;
            padding: 0.35rem 1rem;
            border-radius: 999px;
            font-weight: 700;
            font-size: 1.0rem;
            letter-spacing: 0.02em;
        }
        .swa-tid {
            font-family: monospace;
            background: #f3f4f6;
            padding: 0.15rem 0.5rem;
            border-radius: 6px;
        }
        section[data-testid="stSidebar"] .swa-brand {
            padding: 1rem 0.5rem 0.5rem 0.5rem;
            font-weight: 700;
            font-size: 1.1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def priority_badge_html(priority: str) -> str:
    style = PRIORITY_STYLE.get(priority, UNKNOWN_STYLE)
    return (
        f'<span class="swa-badge" style="background:{style["bg"]}; color:{style["color"]};">'
        f'{style["emoji"]} {priority.upper()}</span>'
    )


# ============================================================
# PAGE: Submit a Complaint
# ============================================================
def page_submit():
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
            Your complaint is processed by three specialized AI agents: **Analysis** (extracts waste
            type, location, duration, severity), **Knowledge retrieval** (finds relevant guidelines),
            and **Decision** (produces a priority and recommendation with reasoning). A final
            **validation layer** either confirms routine cases automatically or escalates uncertain/
            high-risk ones to staff, who make the final call. Priority is based only on objective
            factors — never on who is reporting.
            """
        )

    left, right = st.columns([2, 1])

    with right:
        st.markdown("#### Try an example")
        for label, text in EXAMPLE_COMPLAINTS.items():
            if st.button(label, use_container_width=True, key=f"ex_{label}"):
                st.session_state["complaint_text"] = text

    with left:
        with st.form("complaint_form"):
            location = st.selectbox("Location type", LOCATION_OPTIONS)
            complaint_text = st.text_area(
                "Describe the waste issue",
                value=st.session_state.get("complaint_text", ""),
                placeholder="e.g. There has been a pile of mixed organic and plastic waste behind the school for about 5 days now.",
                height=140,
            )
            submitted = st.form_submit_button("🚀 Submit complaint", use_container_width=True)

        if submitted:
            if not complaint_text.strip():
                st.warning("Please describe the issue before submitting.")
                return
            with st.spinner("Analyzing complaint, retrieving evidence, and generating a recommendation..."):
                try:
                    resp = requests.post(
                        f"{BACKEND_URL}/complaints",
                        json={"text": complaint_text, "location_type": location},
                        timeout=60,
                    )
                    resp.raise_for_status()
                    result = resp.json()
                except requests.exceptions.RequestException as exc:
                    st.error(f"Could not reach the backend: {exc}")
                    return

            tracking_id = new_tracking_id()
            priority = (result.get("priority") or "unknown").lower()
            needs_review = bool(result.get("requires_human_review"))

            record = {
                "id": tracking_id,
                "text": complaint_text,
                "location": location,
                "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "status": "pending_review" if needs_review else "auto_approved",
                "final_action": None if needs_review else result.get("recommended_action"),
                "reviewed_by": None,
                "reviewed_at": None,
                **result,
            }
            st.session_state["complaints"].append(record)
            save_complaints(st.session_state["complaints"])

            if needs_review:
                st.success(
                    f"📥 Complaint logged as **{tracking_id}**. Escalated to staff for review — "
                    "use **Track a Complaint** with this ID later to see the confirmed decision."
                )
            else:
                st.success(f"✅ Complaint logged as **{tracking_id}**. Save this ID to track its status.")

            with st.container(border=True):
                badge_col, review_col = st.columns([1, 2])
                with badge_col:
                    st.markdown(priority_badge_html(priority), unsafe_allow_html=True)
                with review_col:
                    if needs_review:
                        st.warning("⚠️ Pending staff confirmation — the suggestion below is not final.")

                st.markdown("**AI-suggested action**" if needs_review else "**Recommended action**")
                st.write(result.get("recommended_action", "—"))
                st.markdown("**Explanation**")
                st.write(result.get("explanation", "—"))

                sources = result.get("supporting_sources") or []
                if sources:
                    st.markdown("**Supporting sources**")
                    for s in sources:
                        st.markdown(f"- {s}")

                confidence = result.get("confidence")
                if confidence is not None:
                    st.markdown("**Model confidence**")
                    st.progress(min(max(confidence, 0.0), 1.0))
                    st.caption(f"{confidence:.0%}")

            st.caption(
                "This recommendation was generated by an AI system and is intended as decision "
                "support only. Final action requires authorized human sign-off."
            )


# ============================================================
# PAGE: Track a Complaint
# ============================================================
def page_track():
    st.markdown("## 🔎 Track a Complaint")
    st.caption("Enter the tracking ID you received when you submitted your complaint.")

    lookup_id = st.text_input("Tracking ID", placeholder="e.g. WM-2026-7214")
    if st.button("Check status", type="primary"):
        found = find_complaint(lookup_id) if lookup_id else None
        if not found:
            st.error("No complaint found with that tracking ID.")
            return

        priority = (found.get("priority") or "unknown").lower()
        with st.container(border=True):
            st.markdown(priority_badge_html(priority), unsafe_allow_html=True)
            st.markdown(f"**Submitted:** {found['submitted_at']} · {found['location']}")
            st.markdown(f"**Complaint:** {found['text']}")

            if found["status"] == "pending_review":
                st.warning(
                    "⏳ Still under staff review. AI's suggestion "
                    f"(*{found.get('recommended_action', '—')}*) is not yet confirmed."
                )
            elif found["status"] == "resolved":
                st.success(f"✅ **Confirmed action:** {found['final_action']}")
                st.caption(f"Reviewed by `{found['reviewed_by']}` at {found['reviewed_at']}.")
            else:
                st.success(f"✅ **Confirmed action:** {found['final_action']}")
                st.caption("Automatically confirmed — routine case, no escalation needed.")


# ============================================================
# PAGE: Staff
# ============================================================
def page_staff():
    if not st.session_state["auth_token"]:
        st.markdown("## 🔒 Staff Login")
        st.caption("Restricted to authorized waste-management staff.")
        with st.form("staff_login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_submitted = st.form_submit_button("Log in", type="primary")

        if login_submitted:
            if not username or not password:
                st.warning("Enter both a username and password.")
                return
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/auth/login",
                    json={"username": username, "password": password},
                    timeout=15,
                )
                if resp.status_code == 200:
                    token = resp.json().get("access_token") or resp.json().get("token")
                    if token:
                        st.session_state["auth_token"] = token
                        st.session_state["auth_username"] = username
                        st.rerun()
                    else:
                        st.error("Login endpoint returned 200 but no access_token/token field.")
                else:
                    st.error("Invalid username or password.")
            except requests.exceptions.RequestException as exc:
                st.error(f"Could not reach the backend: {exc}")
        return

    top_col, logout_col = st.columns([4, 1])
    with top_col:
        st.markdown(f"## 📋 Complaints Queue — `{st.session_state['auth_username']}`")
    with logout_col:
        if st.button("Log out", use_container_width=True):
            st.session_state["auth_token"] = None
            st.session_state["auth_username"] = None
            st.rerun()

    complaints = st.session_state["complaints"]
    total = len(complaints)
    pending = sum(1 for c in complaints if c["status"] == "pending_review")
    resolved = sum(1 for c in complaints if c["status"] in ("resolved", "auto_approved"))

    m1, m2, m3 = st.columns(3)
    m1.metric("Total complaints", total)
    m2.metric("Needs review", pending)
    m3.metric("Resolved / auto-approved", resolved)

    st.divider()

    if not complaints:
        st.info("No complaints submitted yet.")
        return

    sorted_complaints = sorted(
        complaints,
        key=lambda c: PRIORITY_STYLE.get((c.get("priority") or "").lower(), UNKNOWN_STYLE)["rank"],
    )
    for c in sorted_complaints:
        priority = (c.get("priority") or "unknown").lower()
        with st.container(border=True):
            header_col, status_col = st.columns([3, 1])
            with header_col:
                st.markdown(
                    f'{priority_badge_html(priority)} &nbsp; <span class="swa-tid">{c["id"]}</span> '
                    f'&nbsp; <span style="color:#6b7280; font-size:0.85rem;">{c["submitted_at"]} · {c["location"]}</span>',
                    unsafe_allow_html=True,
                )
            with status_col:
                status_label = {
                    "pending_review": "🚩 **Needs review**",
                    "resolved": "✅ **Resolved**",
                    "auto_approved": "✅ **Auto-approved**",
                }[c["status"]]
                st.markdown(status_label)

            st.write(c["text"])
            st.caption(f"AI-suggested action: {c.get('recommended_action', '—')}")

            if c["status"] == "pending_review":
                st.markdown("**This case needs a human decision:**")
                approve_col, override_col = st.columns([1, 2])
                with approve_col:
                    if st.button("✅ Approve AI suggestion", key=f"approve_{c['id']}"):
                        c["status"] = "resolved"
                        c["final_action"] = c.get("recommended_action")
                        c["reviewed_by"] = st.session_state["auth_username"]
                        c["reviewed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                        save_complaints(st.session_state["complaints"])
                        st.rerun()
                with override_col:
                    override_text = st.text_input(
                        "Or a different action",
                        key=f"override_input_{c['id']}",
                        placeholder="e.g. Send inspector before dispatching crew",
                        label_visibility="collapsed",
                    )
                    if st.button("✏️ Confirm this action instead", key=f"override_btn_{c['id']}"):
                        if override_text.strip():
                            c["status"] = "resolved"
                            c["final_action"] = override_text.strip()
                            c["reviewed_by"] = st.session_state["auth_username"]
                            c["reviewed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                            save_complaints(st.session_state["complaints"])
                            st.rerun()
                        else:
                            st.warning("Enter an action before confirming.")
            elif c["status"] == "resolved":
                st.success(f"**Confirmed:** {c['final_action']}  \n_Reviewed by {c['reviewed_by']} at {c['reviewed_at']}_")
            else:
                st.info(f"**Confirmed:** {c['final_action']} _(auto-approved, routine case)_")


# ============================================================
# App entrypoint
# ============================================================
st.set_page_config(page_title="SmartWaste AI", page_icon="🗑️", layout="wide")

if "complaints" not in st.session_state:
    st.session_state["complaints"] = load_complaints()
if "auth_token" not in st.session_state:
    st.session_state["auth_token"] = None
if "auth_username" not in st.session_state:
    st.session_state["auth_username"] = None

inject_styles()

with st.sidebar:
    st.markdown('<div class="swa-brand">🗑️ SmartWaste AI</div>', unsafe_allow_html=True)

pg = st.navigation(
    [
        st.Page(page_submit, title="Submit a Complaint", icon="📝", default=True),
        st.Page(page_track, title="Track a Complaint", icon="🔎"),
        st.Page(page_staff, title="Staff", icon="🔒"),
    ]
)
pg.run()
