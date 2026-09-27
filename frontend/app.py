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
    timestamp, status_badge, timeline, demo_notice, field,
)

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
LOCATIONS = ["Other", "Residential street", "Near a school", "Near a hospital / clinic",
             "Commercial area", "Industrial area", "Near a water source (river/canal/lake)", "Public park"]


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
    with st.container(key="public_header"):
        header_navigation()
    st.divider()


def header_navigation():
    brand, report, track, access = st.columns([3, 1.35, 1.45, 1.4], vertical_alignment="center")
    with brand:
        st.markdown('<div class="sw-brand"><span aria-hidden="true">♻</span>SmartWaste AI</div>', unsafe_allow_html=True)
        st.caption("Report waste. Track action.")
    report.button("Report Issue", key="nav_report", type="primary", on_click=navigate, args=("report",), width="stretch")
    track.button("Track Complaint", key="nav_track", on_click=navigate, args=("track",), width="stretch")
    if st.session_state.get("auth_token"):
        access.button("Staff Portal", key="nav_staff", on_click=navigate, args=("staff",), width="stretch")
        person, back, exit_col = st.columns([4, 1.5, 1])
        person.text("Signed in as " + st.session_state.get("auth_username", "staff"))
        back.button("Citizen Portal", on_click=navigate, args=("home",), width="stretch")
        exit_col.button("Logout", on_click=logout, width="stretch")
    else:
        access.button("Staff Login", key="nav_login", on_click=navigate, args=("login",), width="stretch")


def public_mode_notice():
    try:
        demo_notice(api("GET", "/ready").get("mode"))
    except ApiError:
        st.info("Service availability could not be checked. If a request fails, please try again.")


def home():
    public_mode_notice()
    st.markdown("""<section class="sw-hero">
      <div class="sw-eyebrow">Waste reporting &amp; tracking</div>
      <h1>Report waste.<br>Track action.</h1>
      <p>Report waste problems quickly. AI-assisted triage with human-reviewed decisions.</p>
      <strong>No account required</strong>
    </section>""", unsafe_allow_html=True)
    with st.container(key="hero_actions"):
        left, right = st.columns(2)
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
            placeholder="Example: Several garbage bags have been left beside the market for three days.")
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
    with st.container(key="login_panel"):
        st.title("Staff Portal")
        st.write("Authorized personnel only")
        if notice := st.session_state.pop("login_notice", None):
            st.error(notice)
        with st.form("login"):
            st.text_input("Username", key="login_username", max_chars=30)
            st.text_input("Password", type="password", key="login_password")
            st.form_submit_button("Sign In", type="primary", width="stretch", on_click=sign_in)


def staff():
    from frontend.staff import staff_portal
    try:
        staff_portal(api)
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
