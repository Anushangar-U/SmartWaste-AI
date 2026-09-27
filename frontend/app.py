"""Public reporting and authenticated staff presentation over the existing API."""
import hashlib
import json
import os
import uuid
from urllib.parse import quote
import requests
import streamlit as st
from dotenv import load_dotenv
from frontend.styles import apply_styles
from frontend.components import (
    STATUS_LABELS, label, timestamp, badges, status_badge, empty_state,
    timeline, demo_notice, evidence_card, field,
)

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
LOCATIONS = ["Other", "Residential street", "Near a school", "Near a hospital / clinic",
             "Commercial area", "Industrial area", "Near a water source (river/canal/lake)", "Public park"]
STATUSES = list(STATUS_LABELS)
PRIORITIES = ["low", "medium", "high", "critical"]


class ApiError(Exception):
    def __init__(self, status):
        self.status = status


def api(method, path, *, protected=False, **kwargs):
    headers = kwargs.pop("headers", {})
    if protected:
        headers["Authorization"] = "Bearer " + st.session_state.get("auth_token", "")
    try:
        response = requests.request(method, BACKEND_URL + path, headers=headers, timeout=180, **kwargs)
        if response.status_code >= 400:
            raise ApiError(response.status_code)
        return response.json()
    except (requests.RequestException, ValueError):
        raise ApiError(503) from None


def clear_staff_session():
    for key in list(st.session_state):
        if key.startswith(("auth_", "staff_", "duplicates_", "duplicate_", "case_", "queue_")):
            del st.session_state[key]


def show_error(error):
    messages = {
        401: "Your session has expired. Please sign in again.",
        403: "Your account is not authorized for this staff action.",
        404: "No matching complaint was found. Please check the tracking ID.",
        409: "This case has changed or the action is unavailable. Refresh the case and review its current status.",
        422: "Please check the required fields and their lengths.",
        429: "Too many requests. Please wait briefly before trying again.",
    }
    message = messages.get(error.status, "We could not reach the service. Please try again. For submissions, retry the same details to avoid duplicates.")
    if error.status in {401, 403}:
        clear_staff_session()
        st.session_state["page"] = "login"
        st.session_state["login_notice"] = message
        st.rerun()
    st.error(message)


def navigate(page):
    st.session_state["page"] = page


def logout():
    clear_staff_session()
    navigate("home")


def render_header():
    brand, report, track, access = st.columns([3, 1.35, 1.45, 1.4], vertical_alignment="center")
    with brand:
        st.markdown('<div class="sw-brand"><span aria-hidden="true">♻</span>SmartWaste AI</div>', unsafe_allow_html=True)
        st.caption("Report waste. Track action.")
    report.button("Report Issue", key="nav_report", on_click=navigate, args=("report",), width="stretch")
    track.button("Track Complaint", key="nav_track", on_click=navigate, args=("track",), width="stretch")
    if st.session_state.get("auth_token"):
        access.button("Staff Portal", key="nav_staff", on_click=navigate, args=("staff",), width="stretch")
        person, back, exit_col = st.columns([4, 1.5, 1])
        person.text("Signed in as " + st.session_state.get("auth_username", "staff"))
        back.button("Citizen Portal", on_click=navigate, args=("home",), width="stretch")
        exit_col.button("Logout", on_click=logout, width="stretch")
    else:
        access.button("Staff Login", key="nav_login", on_click=navigate, args=("login",), width="stretch")
    st.divider()


def public_mode_notice():
    try:
        demo_notice(api("GET", "/ready").get("mode"))
    except ApiError:
        st.info("Service availability could not be checked. If a request fails, please try again.")


def home():
    public_mode_notice()
    st.markdown("""<section class="sw-hero">
      <div class="sw-eyebrow">A cleaner community starts with a report</div>
      <h1>Report waste.<br>Track action.</h1>
      <p>Report waste problems quickly. AI-assisted triage with human-reviewed decisions.</p>
      <strong>No account required</strong>
    </section>""", unsafe_allow_html=True)
    left, right, _ = st.columns([1.4, 1.4, 2])
    left.button("Report an Issue", type="primary", width="stretch", on_click=navigate, args=("report",))
    right.button("Track Complaint", key="hero_track", width="stretch", on_click=navigate, args=("track",))
    st.caption("AI assists staff. Final decisions are made by authorized personnel.")
    st.subheader("How it works")
    st.markdown("""<section class="sw-steps" aria-label="How SmartWaste works">
      <article class="sw-step"><span class="sw-step-number">1</span><h3>Report</h3>
      <p>Describe the waste problem and its general location.</p></article>
      <article class="sw-step"><span class="sw-step-number">2</span><h3>AI Triage</h3>
      <p>Your report is analyzed and supporting guidance is found.</p></article>
      <article class="sw-step"><span class="sw-step-number">3</span><h3>Staff Review</h3>
      <p>Authorized staff review the recommendation and evidence.</p></article>
      <article class="sw-step"><span class="sw-step-number">4</span><h3>Track</h3>
      <p>Check progress using your private tracking ID.</p></article>
    </section>""", unsafe_allow_html=True)


def receipt_panel(record, *, submitted=False):
    with st.container(border=True):
        st.subheader("Complaint submitted" if submitted else "Complaint status")
        if submitted:
            st.success("Your complaint has been saved.")
        demo_notice(record.get("mode"))
        st.caption("Tracking ID")
        st.code(record["tracking_id"], language=None)
        st.caption("Use the copy control on the tracking ID, or select the text to copy it.")
        st.info("Keep this tracking ID private. You will need it to check the complaint status.")
        status_badge(record["status"])
        cols = st.columns(2)
        with cols[0]:
            field("Submitted", timestamp(record.get("submitted_at")))
        with cols[1]:
            field("Last updated", timestamp(record.get("updated_at")))
        if record["status"] == "processing_failed":
            st.warning("Automated processing could not be completed. Your complaint is still saved and can be reviewed by staff.")
        elif record["status"] == "awaiting_review":
            st.info("Your report is waiting for a staff decision.")
        elif record["status"] == "resolved":
            st.success("Staff have marked this complaint as resolved.")
        st.subheader("Progress updates")
        st.caption("Only recorded status changes are shown.")
        timeline(record.get("history", []), current=record["status"])
        for question in record.get("clarification_questions", []):
            st.text("For staff follow-up: " + question)


def report_issue():
    st.button("Back to Home", on_click=navigate, args=("home",))
    st.title("Report a Waste Issue")
    st.write("Tell us what happened and where. No citizen account is required.")
    public_mode_notice()
    if st.session_state.get("receipt"):
        receipt_panel(st.session_state["receipt"], submitted=True)
        cols = st.columns(2)
        cols[0].button("Track this complaint", type="primary", on_click=navigate, args=("track",))
        if cols[1].button("Report another issue"):
            st.session_state.pop("receipt", None)
            st.session_state.pop("submission_fingerprint", None)
            st.session_state.pop("idempotency_key", None)
            st.rerun()
        return
    st.markdown("""<aside class="sw-trust"><strong>Your report, handled with care</strong><br>
      Avoid unnecessary personal information. Keep your tracking ID private.<br>
      AI assists staff; humans make final decisions. External AI providers may process
      complaint text when live mode is enabled.</aside>""", unsafe_allow_html=True)
    with st.form("complaint"):
        st.subheader("1 · Issue details")
        text = st.text_area("Describe what happened", max_chars=2000, height=160,
            placeholder="Example: Household garbage has not been collected from this street for three days...")
        st.subheader("2 · Location")
        location = st.selectbox("Location type", LOCATIONS)
        area = st.text_input("Public area / landmark (optional)", max_chars=120, placeholder="Example: Outside the public library")
        st.caption("Avoid entering a private home address unless necessary.")
        st.subheader("3 · Additional details")
        st.caption("Optional: answer only what you know. Missing details will not prevent submission.")
        duration = st.text_input("How long has it been there? (optional)", max_chars=80, placeholder="Example: Three days")
        hazards = st.selectbox("Hazards visible?", ["Unknown", "Yes", "None observed"],
            help="Chemicals, medical waste or sharp objects. Do not touch or approach the waste to check.")
        submitted = st.form_submit_button("Submit Complaint", type="primary", width="stretch")
    if not submitted:
        return
    if len(text.strip()) < 10:
        st.warning("Please describe the issue in at least 10 characters.")
        return
    if area.strip() and len(area.strip()) < 3:
        st.warning("Please use at least three characters for the public area, or leave it blank.")
        return
    payload = {"text": text.strip(), "location_context": None if location == "Other" else location}
    if area.strip():
        payload["area"] = area.strip()
    hazard_value = {"Unknown": "unknown", "Yes": "visible", "None observed": "none observed"}[hazards]
    if duration.strip() or hazard_value != "unknown":
        payload["clarification_answers"] = {"duration": duration.strip() or None, "hazards": hazard_value}
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    if st.session_state.get("submission_fingerprint") != fingerprint:
        st.session_state["submission_fingerprint"] = fingerprint
        st.session_state["idempotency_key"] = str(uuid.uuid4())
    try:
        with st.spinner("Saving and processing your complaint..."):
            receipt = api("POST", "/complaints", json=payload,
                headers={"Idempotency-Key": st.session_state["idempotency_key"]})
        st.session_state["last_tracking"] = receipt["tracking_id"]
        st.session_state["receipt"] = receipt
        st.rerun()
    except ApiError as exc:
        show_error(exc)


def track_complaint():
    st.button("Back to Home", on_click=navigate, args=("home",))
    st.title("Track a Complaint")
    st.write("Follow your report from submission to resolution. No sign-in needed.")
    with st.form("tracking"):
        tracking = st.text_input("Tracking ID", value=st.session_state.get("last_tracking", ""), max_chars=80,
            placeholder="Paste the private ID from your receipt")
        lookup = st.form_submit_button("Check Status", type="primary")
    if lookup:
        st.session_state.pop("tracking_result", None)
        if not tracking.strip():
            st.warning("Enter the tracking ID from your complaint receipt.")
        else:
            try:
                st.session_state["tracking_result"] = api("GET", "/complaints/track/" + quote(tracking.strip(), safe=""))
            except ApiError as exc:
                show_error(exc)
    if st.session_state.get("tracking_result"):
        receipt_panel(st.session_state["tracking_result"])
    else:
        st.caption("Your tracking ID is private. Staff notes and personal complaint details are not shown here.")


def sign_in():
    # Password exists only as transient widget input; clear it on every outcome.
    try:
        response = api("POST", "/auth/login", data={
            "username": st.session_state.get("login_username", ""),
            "password": st.session_state.get("login_password", "")})
        if response.get("role") not in {"admin", "staff"}:
            st.session_state["login_notice"] = "This account is not authorized for staff access."
        else:
            st.session_state["auth_token"] = response["access_token"]
            st.session_state["auth_username"] = st.session_state.get("login_username", "")
            st.session_state["staff_view"] = "Dashboard"
            navigate("staff")
    except ApiError:
        st.session_state["login_notice"] = "Sign-in was unsuccessful. Check your credentials or try again shortly."
    finally:
        st.session_state["login_password"] = ""


def login():
    st.button("Back to Citizen Portal", on_click=navigate, args=("home",))
    _, middle, _ = st.columns([1, 2, 1])
    with middle:
        st.title("Staff Portal")
        st.write("Authorized personnel only")
        if notice := st.session_state.pop("login_notice", None):
            st.error(notice)
        with st.form("login"):
            st.text_input("Username", key="login_username", max_chars=30)
            st.text_input("Password", type="password", key="login_password")
            st.form_submit_button("Sign In", type="primary", width="stretch", on_click=sign_in)


def change_case(case, action, data):
    try:
        api("POST", f"/staff/complaints/{case['id']}/{action}", protected=True,
            json={"version": case["version"], **data})
        st.rerun()
    except ApiError as exc:
        show_error(exc)


def case_detail(case):
    st.subheader("Original complaint")
    st.text(case["text"])
    st.text("Location: " + (case.get("location_context") or "Not supplied"))
    st.text("Reported area: " + (case.get("area") or "Not supplied"))
    st.caption("Submitted: " + case["submitted_at"])
    st.caption("Processing mode: " + case.get("processing_mode", "unknown"))
    st.subheader("AI analysis")
    st.json(case.get("analysis") or {"status": "Not available"})
    retrieval = case.get("retrieval") or {}
    st.subheader("Supporting evidence")
    st.caption("Supporting evidence retrieved: " + ("Yes" if retrieval.get("evidence") else "No"))
    st.caption("Claim verification: not independently verified.")
    for issue in (retrieval.get("citation_validation") or {}).get("issues", []):
        st.warning(issue)
    if retrieval.get("answer"):
        st.text(retrieval["answer"])
    for number, item in enumerate(retrieval.get("evidence", []), 1):
        with st.expander(f"Passage [{number}]"):
            st.text(item.get("title") or item["source"])
            st.caption(f"PDF page {item['page']} | semantic similarity {item['score']:.3f} (not probability)")
            st.text(item["text"])
    decision = case.get("decision") or {}
    st.subheader("AI recommendation")
    st.text("Priority: " + decision.get("priority", "Unavailable"))
    st.text("Review urgency: " + case.get("review_urgency", "normal"))
    for question in decision.get("clarification_questions", []):
        st.info(question)
    st.text(decision.get("recommended_action", "No automated recommendation."))
    st.text(decision.get("explanation", ""))
    st.caption(f"Model-reported confidence: {decision.get('confidence', 0):.0%}; not calibrated probability.")
    for note in [*(decision.get("validation") or {}).get("issues", []), *(case.get("validation") or {}).get("warnings", [])]:
        st.warning(note)
    st.subheader("Human decision")
    st.text("Review: " + (case.get("review_decision") or "Pending"))
    if case.get("reviewer"):
        st.text(f"Reviewer: {case['reviewer']} | {case.get('reviewed_at')}")
        st.text(case.get("review_reason") or "")
        st.text(case.get("human_action") or "")
    if case.get("error_stage"):
        st.warning("Automated processing failed at the " + case["error_stage"] + " stage. Partial results are retained.")
    if case["status"] in {"awaiting_review", "processing_failed"}:
        with st.form("review"):
            choice = st.selectbox("Review decision", ["approve", "override"])
            reason = st.text_area("Review reason", max_chars=2000)
            priority = st.selectbox("Override priority", PRIORITIES)
            action = st.text_area("Override action", max_chars=2000)
            send = st.form_submit_button("Save review")
        if send:
            change_case(case, "review", {"decision": choice, "reason": reason,
                "priority": priority if choice == "override" else None,
                "action": action if choice == "override" else None})
    if case["status"] == "reviewed":
        with st.form("assign"):
            assignee = st.text_input("Assign to team", max_chars=120)
            send = st.form_submit_button("Assign complaint")
        if send:
            change_case(case, "assign", {"assignee": assignee})
    if case["status"] == "assigned":
        st.text("Assigned to: " + (case.get("assignee") or ""))
        with st.form("resolve"):
            note = st.text_area("Resolution note (staff only)", max_chars=2000)
            send = st.form_submit_button("Mark resolved")
        if send:
            change_case(case, "resolve", {"note": note})
    if case["status"] in {"processing_failed", "processing"} and st.button("Retry failed or interrupted processing"):
        change_case(case, "retry", {})
    with st.expander("Case history"):
        st.dataframe(case.get("history", []), hide_index=True)
    with st.expander("Possible duplicate incidents"):
        if st.button("Find possible duplicates"):
            try:
                st.session_state["duplicates_" + case["id"]] = api("GET", f"/staff/complaints/{case['id']}/duplicates", protected=True)
            except ApiError as exc:
                show_error(exc)
        data = st.session_state.get("duplicates_" + case["id"], {})
        if data.get("reason"):
            st.info(data["reason"])
        for candidate in data.get("suggestions", []):
            st.text(candidate["tracking_id"])
            st.caption(candidate["reason"] + f" Similarity: {candidate['similarity']:.3f}")
            reason = st.text_input("Why are these the same incident?", key="duplicate_reason_" + candidate["id"], max_chars=1000)
            if st.button("Confirm link (retain both complaints)", key="duplicate_" + candidate["id"]):
                change_case(case, "duplicate", {"other_id": candidate["id"], "reason": reason})
        if data.get("confirmed_links"):
            st.caption("Previously confirmed links")
            st.dataframe(data["confirmed_links"], hide_index=True)


def staff():
    st.header("Staff workspace")
    if not st.session_state.get("auth_token"):
        with st.form("login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            send = st.form_submit_button("Log in")
        if send:
            try:
                response = api("POST", "/auth/login", data={"username": username, "password": password})
                if response.get("role") not in {"admin", "staff"}:
                    st.error("This account is not authorized for staff access.")
                else:
                    st.session_state["auth_token"] = response["access_token"]
                    st.rerun()
            except ApiError as exc:
                show_error(exc)
        return
    if st.button("Log out"):
        st.session_state.pop("auth_token", None)
        st.rerun()
    st.caption("This queue is shared through the backend database.")
    try:
        stats = api("GET", "/staff/dashboard", protected=True)
        with st.expander("Operational dashboard", expanded=True):
            counters = st.columns(4)
            counters[0].metric("Submitted records", stats["total"])
            counters[1].metric("Review backlog", stats["review_backlog"])
            counters[2].metric("Assigned", stats["by_status"].get("assigned", 0))
            counters[3].metric("Resolved", stats["by_status"].get("resolved", 0))
            st.caption("Record modes (demo/live/unknown): " + str(stats["record_modes"]))
            if stats["average_resolution_hours"] is not None:
                st.caption(f"Resolution hours: average {stats['average_resolution_hours']:.2f}; median {stats['median_resolution_hours']:.2f} ({stats['resolution_samples']} cases)")
            else:
                st.caption("Resolution time: not enough completed cases (minimum two).")
            st.dataframe([{"status": key, "count": value} for key,value in stats["by_status"].items()], hide_index=True)
            st.dataframe([{"priority": key, "count": value} for key,value in stats["by_priority"].items()], hide_index=True)
            st.dataframe([{"reported_area": key, "count": value} for key,value in stats["by_area"].items()], hide_index=True)
    except ApiError as exc:
        show_error(exc)
        return
    cols = st.columns(3)
    status = cols[0].selectbox("Status filter", ["All", *STATUSES])
    priority = cols[1].selectbox("Priority filter", ["All", *PRIORITIES])
    review_needed = cols[2].checkbox("Review needed only")
    search = st.text_input("Search complaint, tracking ID or location", max_chars=120)
    page = st.number_input("Queue page", min_value=1, value=1, step=1)
    params = {"limit": 50, "offset": (page - 1) * 50}
    if status != "All":
        params["status"] = status
    if priority != "All":
        params["priority"] = priority
    if review_needed:
        params["review_needed"] = True
    if search:
        params["search"] = search
    try:
        records = api("GET", "/staff/complaints", protected=True, params=params)
        if not records:
            st.info("No complaints match these filters.")
            return
        st.dataframe([{"tracking_id": r["tracking_id"], "status": r["status"],
            "priority": r.get("human_priority") or (r.get("decision") or {}).get("priority", "unknown"),
            "location": r.get("location_context"), "review_required": r["requires_human_review"]} for r in records],
            hide_index=True, use_container_width=True)
        options = {r["id"]: r["tracking_id"] for r in records}
        selected = st.selectbox("Open case", list(options), format_func=options.get)
        case_detail(api("GET", "/staff/complaints/" + selected, protected=True))
    except ApiError as exc:
        show_error(exc)


st.set_page_config(page_title="SmartWaste AI · Report waste. Track action.", page_icon="♻", layout="wide")
apply_styles()
render_header()
page = st.session_state.get("page", "home")
if page == "report":
    report_issue()
elif page == "track":
    track_complaint()
elif page == "login":
    login()
elif page == "staff":
    if st.session_state.get("auth_token"):
        staff()
    else:
        login()
else:
    home()
st.divider()
st.caption("SmartWaste AI · University demonstration · AI-assisted reporting with human-reviewed action.")
