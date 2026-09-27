"""Citizen tracking and authorized staff case management."""
import hashlib
import json
import os
import uuid
from urllib.parse import quote
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
LOCATIONS = ["Other", "Residential street", "Near a school", "Near a hospital / clinic",
             "Commercial area", "Industrial area", "Near a water source (river/canal/lake)", "Public park"]
STATUSES = ["submitted", "processing", "awaiting_review", "reviewed", "assigned", "processing_failed", "resolved"]
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


def show_error(error):
    messages = {401: "Please sign in again.", 403: "Your account cannot perform this action.",
        404: "No matching record was found.", 409: "The record changed or this action is unavailable. Refresh and check its status.",
        422: "Please check input lengths and required fields.", 429: "Please wait briefly before trying again."}
    st.error(messages.get(error.status, "Service temporarily unavailable. Retry the same submission to avoid duplicates."))
    if error.status == 401:
        st.session_state.pop("auth_token", None)


def status_panel(record):
    st.success("Complaint saved. Keep your tracking ID private.")
    st.code(record["tracking_id"], language=None)
    st.metric("Status", record["status"].replace("_", " ").title())
    if record["status"] == "processing_failed":
        st.warning("Automated processing is unavailable. Your complaint is saved for staff review.")
    elif record["status"] == "awaiting_review":
        st.info("Staff must review the recommendation before assignment.")
    st.dataframe(record.get("history", []), hide_index=True, use_container_width=True)
    for question in record.get("clarification_questions", []):
        st.info("For staff follow-up: " + question)


def citizen():
    st.header("Report a waste problem")
    try:
        if api("GET", "/ready").get("mode") == "mock_demo":
            st.warning("Demonstration mode: AI analysis and evidence are synthetic examples.")
    except ApiError:
        st.info("Some processing dependencies may be unavailable. Submissions are still saved when the backend is reachable.")
    st.caption("Complaint text may be processed by configured external AI providers. Avoid unnecessary personal or sensitive information.")
    with st.form("complaint"):
        text = st.text_area("Describe the waste issue", max_chars=2000, height=130)
        location = st.selectbox("Location type", LOCATIONS)
        area = st.text_input("Public area or landmark (optional; avoid personal addresses)", max_chars=120)
        st.caption("Optional clarification: answer only what you know. You can submit without these details.")
        duration = st.text_input("How long has it been present? (optional)", max_chars=80)
        hazards = st.selectbox("Visible chemicals, medical waste or sharp objects? Do not approach to check.", ["unknown", "visible", "none observed"])
        submitted = st.form_submit_button("Submit complaint")
    if submitted:
        if len(text.strip()) < 10:
            st.warning("Please provide at least 10 nonblank characters.")
        else:
            payload = {"text": text.strip(), "location_context": None if location == "Other" else location}
            if area.strip():
                payload["area"] = area.strip()
            if duration.strip() or hazards != "unknown":
                payload["clarification_answers"] = {"duration": duration.strip() or None, "hazards": hazards}
            fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
            if st.session_state.get("submission_fingerprint") != fingerprint:
                st.session_state["submission_fingerprint"] = fingerprint
                st.session_state["idempotency_key"] = str(uuid.uuid4())
            try:
                with st.spinner("Saving and processing your complaint..."):
                    receipt = api("POST", "/complaints", json=payload,
                        headers={"Idempotency-Key": st.session_state["idempotency_key"]})
                st.session_state["last_tracking"] = receipt["tracking_id"]
                status_panel(receipt)
            except ApiError as exc:
                show_error(exc)
    st.divider()
    st.subheader("Track a complaint")
    with st.form("tracking"):
        tracking = st.text_input("Tracking ID", value=st.session_state.get("last_tracking", ""), max_chars=80)
        lookup = st.form_submit_button("Check status")
    if lookup and tracking.strip():
        try:
            status_panel(api("GET", "/complaints/track/" + quote(tracking.strip(), safe="")))
        except ApiError as exc:
            show_error(exc)


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


st.set_page_config(page_title="SmartWaste AI", page_icon="♻", layout="wide")
st.title("SmartWaste AI")
st.caption("Evidence-supported triage with authorized human decisions.")
mode = st.sidebar.radio("Workspace", ["Citizen", "Staff"])
if mode == "Citizen":
    citizen()
else:
    staff()
