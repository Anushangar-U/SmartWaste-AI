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
WASTE_TYPES = {
    "Household / mixed waste": "household_mixed",
    "Food / organic waste": "food_organic",
    "Plastic": "plastic",
    "Paper / cardboard": "paper_cardboard",
    "Glass": "glass",
    "Sharp / rusty metal": "metal_sharp",
    "Construction debris": "construction_debris",
    "Electronic waste": "e_waste",
    "Batteries": "batteries",
    "Medical waste": "medical_waste",
    "Needles / sharps": "sharps_needles",
    "Chemicals": "chemicals",
    "Pesticides / herbicides": "pesticides",
    "Paint / solvent / oil / fuel": "paint_solvent_oil_fuel",
    "Industrial waste": "industrial_waste",
    "Garden waste": "garden_waste",
    "Animal waste / carcass": "animal_waste_carcass",
    "Other": "other",
    "Unknown / not sure": "unknown",
}
PROBLEM_TYPES = {
    "Uncollected waste": "uncollected", "Illegal dumping": "illegal_dumping",
    "Overflowing bin": "overflowing_bin", "Roadside litter": "roadside_litter",
    "Burning waste": "burning", "Leaking / spilled waste": "leaking_spill",
    "Blocked drain caused by waste": "blocked_drain", "Repeated dumping": "recurring_dumping",
    "Abandoned electronics": "abandoned_electronics", "Other": "other", "Unknown / not sure": "unknown",
}
AMOUNTS = {"Single item": "single_item", "Very small": "very_small", "Small": "small",
    "Medium pile": "medium", "Large pile": "large", "Very large / truck-load size": "very_large",
    "Unknown / not sure": "unknown"}
CONDITIONS = {"Dry": "dry", "Wet": "wet", "Leaking": "leaking", "Burning / smoking": "burning_smoking",
    "Decomposing": "decomposing", "Damaged / broken": "damaged_broken", "Swollen battery": "swollen_battery",
    "Mixed condition": "mixed", "Unknown / not sure": "unknown"}
HAZARDS = {"No hazards observed": "none_observed", "Unknown / not sure": "unknown",
    "Needles / sharps": "sharps_needles", "Broken glass": "broken_glass",
    "Rusty / sharp metal": "rusty_sharp_metal", "Medical material": "medical_material",
    "Chemical container": "chemical_container", "Chemical leak / spill": "chemical_leak",
    "Damaged / swollen battery": "damaged_battery", "Smoke / fire": "smoke_fire",
    "Strong fumes": "strong_fumes", "Animal carcass": "animal_carcass",
    "Insects / rodents": "pests", "Other": "other"}
LOCATION_TYPES = {"Residential area": "residential", "School area": "school_area",
    "Hospital / clinic area": "hospital_clinic", "Commercial area": "commercial",
    "Industrial area": "industrial", "Park": "park", "Roadside": "roadside",
    "Open land": "open_land", "Waterway / drain": "waterway_drain",
    "Collection point / bin area": "collection_point", "Other": "other", "Unknown / not sure": "unknown"}
NEARBY = {"None": "none", "School": "school", "Hospital / clinic": "hospital",
    "Food market": "food_market", "Playground": "playground", "Waterway": "waterway",
    "Storm drain": "storm_drain", "Busy road": "busy_road", "Residential homes": "residential_homes",
    "Other": "other", "Unknown / not sure": "unknown"}
PLACEMENTS = {"Roadside": "roadside", "Footpath": "footpath", "Inside drain": "inside_drain",
    "Beside water": "beside_water", "Open land": "open_land", "Alley": "alley",
    "Collection point / bin": "collection_point_bin", "Public area": "public_area",
    "Private property visible from public area": "private_property_visible_from_public",
    "Other": "other", "Unknown / not sure": "unknown"}
DURATIONS = {"Less than 24 hours": "less_than_24h", "1–3 days": "one_to_three_days",
    "4–7 days": "four_to_seven_days", "1–4 weeks": "one_to_four_weeks",
    "Over one month": "over_one_month", "Unknown / not sure": "unknown"}
RECURRENCE = {"First occurrence": "first_occurrence", "Has happened before": "happened_before",
    "Repeatedly happens here": "repeated_here", "Continuously present": "continuously_present",
    "Unknown / not sure": "unknown"}
IMPACTS = {"No obvious effect": "none_observed", "Unknown / not sure": "unknown",
    "Bad smell": "bad_smell", "Insects / rodents": "pests", "Blocked drainage": "blocked_drainage",
    "Water contamination concern": "water_contamination_concern", "Smoke": "smoke",
    "Blocking road / footpath": "road_or_footpath_obstruction",
    "People / children nearby": "people_children_nearby", "Other": "other"}
EXPOSURES = {"No one exposed / injured": "none", "Cut or puncture": "cut_or_puncture",
    "Needlestick": "needlestick", "Skin contact": "skin_contact", "Eye contact": "eye_contact",
    "Inhaled fumes / smoke": "inhalation", "Swallowed material": "ingestion",
    "Burn": "burn", "Other": "other", "Unknown / not sure": "unknown"}


class ApiError(Exception):
    def __init__(self, status):
        self.status = status


def api(method, path, *, protected=False, raw=False, **kwargs):
    headers = kwargs.pop("headers", {})
    if protected:
        headers["Authorization"] = "Bearer " + st.session_state.get("auth_token", "")
    try:
        response = requests.request(method, BACKEND_URL + path, headers=headers, timeout=180, **kwargs)
        if response.status_code >= 400:
            raise ApiError(response.status_code)
        return response.content if raw else response.json()
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
    if st.session_state.get("auth_token"):
        brand, track, exit_col = st.columns([5, 1.5, 1.1], vertical_alignment="center")
        with brand:
            st.markdown('<div class="sw-brand"><span aria-hidden="true">♻</span>SmartWaste AI</div>', unsafe_allow_html=True)
            st.caption("Report waste. Track action.")
        track.button("Track Complaint", key="nav_track_staff", on_click=navigate, args=("track",), width="stretch")
        exit_col.button("Logout", on_click=logout, width="stretch")
    else:
        brand, access = st.columns([5, 1.4], vertical_alignment="center")
        with brand:
            st.markdown('<div class="sw-brand"><span aria-hidden="true">♻</span>SmartWaste AI</div>', unsafe_allow_html=True)
            st.caption("Report waste. Track action.")
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

        guidance = record.get("guidance")
        if guidance:
            st.divider()
            st.subheader("Safety & disposal guidance for this report")
            field("Risk level", guidance.get("risk_level", "Not recorded").replace("_", " ").title())
            field("Reported waste", guidance.get("waste_summary"))
            st.caption(guidance.get("reason", ""))
            sections = [
                ("Immediate precautions", guidance.get("immediate_precautions", [])),
                ("How to dispose / hand over safely", guidance.get("disposal_steps", [])),
                ("If someone was exposed or injured", guidance.get("if_exposed", [])),
                ("Seek urgent help if", guidance.get("seek_urgent_help", [])),
                ("Do not", guidance.get("do_not", [])),
            ]
            for title, items in sections:
                if items:
                    st.markdown("**" + title + "**")
                    for item in items:
                        st.markdown("- " + item)
            if guidance.get("sources"):
                st.markdown("**Authoritative references used for safety rules**")
                for source in guidance["sources"]:
                    st.text(source.get("issuer", "") + " — " + source.get("title", ""))
            st.info(guidance.get("evidence_note", ""))


def report_issue():
    st.button("Back to Home", on_click=navigate, args=("home",))
    st.title("Report a Waste Issue")
    st.write("Complete the required details so the system can triage the complaint accurately.")
    public_mode_notice()
    if st.session_state.get("receipt"):
        receipt_panel(st.session_state["receipt"], submitted=True)
        cols = st.columns(2)
        cols[0].button("Track this complaint", type="primary", on_click=navigate, args=("track",))
        if cols[1].button("Report another issue"):
            for key in ["receipt", "submission_fingerprint", "idempotency_key"]:
                st.session_state.pop(key, None)
            st.rerun()
        return

    st.markdown("""<aside class="sw-trust"><strong>Required structured report</strong><br>
      Choose <em>Unknown / not sure</em> when you genuinely do not know an answer.
      Do not approach, touch or smell hazardous waste just to complete this form.
      Photo evidence is optional.</aside>""", unsafe_allow_html=True)

    with st.form("complaint"):
        st.subheader("1 · Waste details")
        waste_labels = st.multiselect("Waste type(s) *", list(WASTE_TYPES), placeholder="Select one or more")
        specific_items = st.text_input("What specific items can you see? *", max_chars=240,
            placeholder="Example: old laptop, swollen battery, broken metal sheets")
        problem_label = st.selectbox("Main problem *", list(PROBLEM_TYPES), index=None, placeholder="Select")
        amount_label = st.selectbox("Estimated amount *", list(AMOUNTS), index=None, placeholder="Select")
        condition_label = st.selectbox("Condition of the waste *", list(CONDITIONS), index=None, placeholder="Select")

        st.subheader("2 · Safety details")
        hazard_labels = st.multiselect("Visible hazards *", list(HAZARDS), placeholder="Select at least one")
        exposure_label = st.selectbox("Has anyone been exposed or injured? *", list(EXPOSURES), index=None, placeholder="Select")
        material_label = st.text_input("Product / chemical / battery label *", max_chars=160,
            placeholder="Type the visible name, or type Unknown if no label is safely visible")

        st.subheader("3 · Location")
        location_label = st.selectbox("Location type *", list(LOCATION_TYPES), index=None, placeholder="Select")
        area = st.text_input("Public area / landmark *", max_chars=160,
            placeholder="Example: Outside Nugegoda public market")
        nearby_label = st.selectbox("Nearby sensitive place *", list(NEARBY), index=None, placeholder="Select")
        placement_label = st.selectbox("Where exactly is the waste? *", list(PLACEMENTS), index=None, placeholder="Select")
        st.caption("Use a public landmark. Avoid unnecessary private home addresses.")

        st.subheader("4 · Time and impact")
        duration_label = st.selectbox("How long has it been there? *", list(DURATIONS), index=None, placeholder="Select")
        recurrence_label = st.selectbox("Is this a recurring problem? *", list(RECURRENCE), index=None, placeholder="Select")
        impact_labels = st.multiselect("Current effects / impacts *", list(IMPACTS), placeholder="Select at least one")

        st.subheader("5 · Description")
        text = st.text_area("Describe what happened *", max_chars=2000, height=160,
            placeholder="Add useful context that is not already captured above.")

        st.subheader("6 · Photo evidence")
        st.caption("Optional. Upload a clear photo only if it is safe to do so. Never approach hazardous waste for a photo.")
        photo = st.file_uploader("Photo (optional)", type=["jpg", "jpeg", "png", "webp",], accept_multiple_files=False)
        if photo is not None:
            st.image(photo, caption="Selected photo preview", width="stretch")
        submitted = st.form_submit_button("Submit Complaint", type="primary", width="stretch")

    if not submitted:
        return

    missing = []
    if not waste_labels: missing.append("waste type")
    if len(specific_items.strip()) < 3: missing.append("specific items")
    if not problem_label: missing.append("main problem")
    if not amount_label: missing.append("amount")
    if not condition_label: missing.append("condition")
    if not hazard_labels: missing.append("visible hazards")
    if not exposure_label: missing.append("exposure / injury")
    if len(material_label.strip()) < 2: missing.append("product/material label")
    if not location_label: missing.append("location type")
    if len(area.strip()) < 3: missing.append("public area / landmark")
    if not nearby_label: missing.append("nearby sensitive place")
    if not placement_label: missing.append("waste placement")
    if not duration_label: missing.append("duration")
    if not recurrence_label: missing.append("recurrence")
    if not impact_labels: missing.append("effects / impacts")
    if len(text.strip()) < 20: missing.append("description (at least 20 characters)")
    if missing:
        st.warning("Complete all required fields: " + ", ".join(missing) + ".")
        return

    waste_values = [WASTE_TYPES[label] for label in waste_labels]
    hazard_values = [HAZARDS[label] for label in hazard_labels]
    impact_values = [IMPACTS[label] for label in impact_labels]
    if "unknown" in waste_values and len(waste_values) > 1:
        st.warning("Choose either 'Unknown / not sure' or identified waste types, not both.")
        return
    if any(value in hazard_values for value in ["none_observed", "unknown"]) and len(hazard_values) > 1:
        st.warning("Choose either 'No hazards observed' / 'Unknown' or specific hazards, not both.")
        return
    if any(value in impact_values for value in ["none_observed", "unknown"]) and len(impact_values) > 1:
        st.warning("Choose either 'No obvious effect' / 'Unknown' or specific effects, not both.")
        return

    intake = {
        "waste_types": waste_values,
        "specific_items": specific_items.strip(),
        "problem_type": PROBLEM_TYPES[problem_label],
        "amount": AMOUNTS[amount_label],
        "condition": CONDITIONS[condition_label],
        "hazards": hazard_values,
        "location_type": LOCATION_TYPES[location_label],
        "area_landmark": area.strip(),
        "nearby_sensitive_place": NEARBY[nearby_label],
        "placement": PLACEMENTS[placement_label],
        "duration": DURATIONS[duration_label],
        "recurrence": RECURRENCE[recurrence_label],
        "impacts": impact_values,
        "exposure": EXPOSURES[exposure_label],
        "material_label": material_label.strip(),
    }
    payload = {"text": text.strip(), "intake": intake}
    photo_bytes = photo.getvalue() if photo is not None else None
    photo_hash = hashlib.sha256(photo_bytes).hexdigest() if photo_bytes else None
    fingerprint = hashlib.sha256(json.dumps([payload, photo_hash], sort_keys=True).encode()).hexdigest()
    if st.session_state.get("submission_fingerprint") != fingerprint:
        st.session_state["submission_fingerprint"] = fingerprint
        st.session_state["idempotency_key"] = str(uuid.uuid4())

    try:
        with st.spinner("Saving and processing your complaint..."):
            headers = {"Idempotency-Key": st.session_state["idempotency_key"]}
            if photo_bytes:
                receipt = api("POST", "/complaints/structured-with-photo",
                    data={"text": payload["text"], "intake_json": json.dumps(intake)},
                    files={"photo": (photo.name, photo_bytes, photo.type or "application/octet-stream")},
                    headers=headers)
            else:
                receipt = api("POST", "/complaints/structured", json=payload, headers=headers)
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
