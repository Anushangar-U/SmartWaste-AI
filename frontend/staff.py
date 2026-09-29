"""Staff presentation using injected API/error handlers and unchanged backend contracts."""
import streamlit as st
from frontend.components import (
    STATUS_LABELS, label, timestamp, badges, status_badge, empty_state,
    timeline, demo_notice, evidence_card, field,
)

VIEWS = ["Dashboard", "Complaints", "Needs Review", "Assigned", "Resolved"]
PRIORITIES = ["low", "medium", "high", "critical"]


def choose_view(view):
    st.session_state["staff_view"] = view
    st.session_state.pop("staff_case_id", None)


def leave_case():
    st.session_state.pop("staff_case_id", None)
    st.session_state.pop("staff_case_snapshot", None)


class StaffPortal:
    def __init__(self, api):
        self.api = api

    def get(self, path, **kwargs):
        return self.api("GET", path, protected=True, **kwargs)

    def change(self, case, action, data):
        # Use the version the form was first shown with, not a fresh rerun's version.
        # This lets the backend reject actions based on a stale human decision.
        snapshot = st.session_state.get("staff_case_snapshot", (case["id"], case["version"]))
        self.api("POST", f"/staff/complaints/{case['id']}/{action}", protected=True,
                 json={"version": snapshot[1], **data})
        st.session_state.pop("staff_case_snapshot", None)
        st.session_state["staff_notice"] = {
            "review": "Human decision saved.", "assign": "Complaint assigned.",
            "resolve": "Complaint marked as resolved.", "retry": "Processing attempt finished. Review the current status below.",
            "duplicate": "Duplicate link saved. Both original complaints are retained.",
        }[action]
        if action == "duplicate":
            st.session_state.pop("duplicates_" + case["id"], None)
        st.rerun()

    def render(self):
        st.title("Staff Portal")
        st.caption("Review evidence. Make the human decision. Follow each case through to resolution.")
        st.session_state.setdefault("staff_view", "Dashboard")
        st.segmented_control("Staff navigation", VIEWS, key="staff_view",
                             on_change=leave_case, width="stretch")
        if notice := st.session_state.pop("staff_notice", None):
            st.success(notice)
        if st.session_state.get("staff_case_id"):
            self.detail(self.get("/staff/complaints/" + st.session_state["staff_case_id"]))
        elif st.session_state.get("staff_view") in {None, "Dashboard"}:
            self.dashboard()
        else:
            self.queue()

    def dashboard(self):
        stats = self.get("/staff/dashboard")
        st.subheader("Your service at a glance")
        st.caption("Counts reflect stored complaints. Linked duplicate reports remain separate records.")
        cols = st.columns(4)
        for col, title, value in zip(cols,
                ["Total Complaints", "Awaiting Review", "Assigned", "Resolved"],
                [stats["total"], stats["by_status"].get("awaiting_review", 0),
                 stats["by_status"].get("assigned", 0), stats["by_status"].get("resolved", 0)]):
            col.metric(title, value)
        st.info(f"Review backlog: {stats['review_backlog']} complaints awaiting processing or a staff decision.")
        left, right = st.columns(2)
        left.button("Open Complaints", type="primary", width="stretch", on_click=choose_view, args=("Complaints",))
        right.button("Review waiting cases", width="stretch", on_click=choose_view, args=("Needs Review",))
        if not stats["total"]:
            empty_state("Ready for the first report", "Citizen submissions will appear here automatically. Use Citizen Portal to submit a report.")
        cols = st.columns(2)
        with cols[0]:
            self.distribution("Priority distribution", "Priority", stats["by_priority"])
        with cols[1]:
            self.distribution("Status distribution", "Status", stats["by_status"])
        cols = st.columns(2)
        with cols[0]:
            self.distribution("Reported areas", "Area", stats["by_area"], humanize=False)
        with cols[1], st.container(border=True):
            st.subheader("Resolution time")
            if stats.get("average_resolution_hours") is not None:
                st.metric("Average hours", f"{stats['average_resolution_hours']:.1f}")
                st.metric("Median hours", f"{stats['median_resolution_hours']:.1f}")
                st.caption(f"Based on {stats['resolution_samples']} resolved complaints.")
            else:
                st.write("No resolution statistics yet. At least two completed cases are needed.")
                if not stats["by_status"].get("resolved", 0):
                    st.caption("No resolved cases yet.")
        with st.expander("About these records"):
            for mode, count in stats["record_modes"].items():
                name = {"mock_demo": "Demonstration · synthetic AI", "live": "Live processing", "unknown": "Processing mode not recorded"}.get(mode, "Other")
                st.text(f"{name}: {count}")

    @staticmethod
    def distribution(title, column, values, humanize=True):
        with st.container(border=True):
            st.subheader(title)
            if values:
                st.dataframe([{column: label(k) if humanize else k, "Complaints": v}
                              for k, v in values.items()], hide_index=True, width="stretch")
            else:
                st.caption("This summary will appear when complaints are available.")

    def queue(self):
        view = st.session_state.get("staff_view", "Complaints")
        st.subheader(view)
        with st.container(border=True):
            st.caption("FILTER COMPLAINTS")
            search = st.text_input("Search complaint, tracking ID or location", max_chars=120, key="queue_search")
            cols = st.columns(3)
            fixed = {"Assigned": "assigned", "Resolved": "resolved"}.get(view)
            status = cols[0].selectbox("Status", ["All", *STATUS_LABELS],
                index=list(STATUS_LABELS).index(fixed) + 1 if fixed else 0,
                format_func=label, disabled=bool(fixed), key="queue_status_" + view)
            priority = cols[1].selectbox("Priority", ["All", *PRIORITIES], format_func=label, key="queue_priority")
            review = cols[2].checkbox("Review Required", value=view == "Needs Review",
                                     disabled=view == "Needs Review", key="queue_review_" + view)
            st.caption("Urgent reviews are listed first. Filters apply across the shared backend queue.")
        # A changed filter always returns to page one.
        signature = (view, search, status, priority, review)
        if st.session_state.get("queue_signature") != signature:
            st.session_state["queue_signature"] = signature
            st.session_state["queue_page"] = 1
        page = st.number_input("Queue page", min_value=1, value=None, step=1, key="queue_page") or 1
        params = {"limit": 20, "offset": (page - 1) * 20}
        if fixed or status != "All":
            params["status"] = fixed or status
        if priority != "All":
            params["priority"] = priority
        if review or view == "Needs Review":
            params["review_needed"] = True
        if search.strip():
            params["search"] = search.strip()
        records = self.get("/staff/complaints", params=params)
        if not records:
            title = "No complaints currently require review." if view == "Needs Review" else "No complaints match these filters."
            empty_state(title, "Try adjusting your filters or returning to page one.")
            return
        st.caption(f"Page {page} · {len(records)} reports shown · Up to 20 per page")
        # Compact cards stack naturally on narrow screens; no wide interactive grid required.
        for case in records:
            with st.container(border=True):
                main, action = st.columns([4, 1])
                with main:
                    summary = (case.get("analysis") or {}).get("summary") or case["text"]
                    st.text(summary[:180] + ("…" if len(summary) > 180 else ""))
                    priority = case.get("human_priority") or (case.get("decision") or {}).get("priority")
                    urgency = case.get("review_urgency", "normal")
                    badges((label(case["status"]), {"resolved": "success", "processing_failed": "danger", "awaiting_review": "attention", "assigned": "info"}.get(case["status"], "")),
                           ("Priority: " + label(priority), "danger" if priority == "critical" else "attention" if priority == "high" else ""),
                           ("Review: " + ("Required" if case["requires_human_review"] else "Not flagged"), "attention" if case["requires_human_review"] else ""),
                           ("Urgency: " + label(urgency), "danger" if urgency == "urgent" else ""))
                    st.text("Area: " + (case.get("area") or case.get("location_context") or "Not supplied"))
                    st.text("Tracking ID: " + case["tracking_id"])
                    st.caption("Submitted " + timestamp(case["submitted_at"]))
                if action.button("Open Case", key="case_open_" + case["id"], width="stretch"):
                    st.session_state["staff_case_id"] = case["id"]
                    st.rerun()

    def detail(self, case):
        snapshot = st.session_state.get("staff_case_snapshot")
        if not snapshot or snapshot[0] != case["id"]:
            st.session_state["staff_case_snapshot"] = (case["id"], case["version"])
        left, right = st.columns([4, 1])
        left.button("Back to complaint queue", on_click=leave_case)
        if right.button("Refresh Case", width="stretch"):
            # Explicitly discard old action inputs before accepting the current version.
            for key in list(st.session_state):
                if key.startswith("case_"):
                    del st.session_state[key]
            st.session_state.pop("staff_case_snapshot", None)
            st.rerun()
        if snapshot and snapshot[0] == case["id"] and snapshot[1] != case["version"]:
            st.warning("This case changed since you opened it. Refresh Case and check the latest details before taking action.")
        st.subheader("Case Overview")
        st.caption("Tracking ID")
        st.code(case["tracking_id"], language=None)
        status_badge(case["status"])
        demo_notice(case.get("processing_mode"))
        if case["status"] == "processing_failed":
            st.warning("Automated Processing Incomplete. The complaint is safely stored. Staff may retry processing or handle the case manually. Available partial results are shown below.")
        tabs = st.tabs(["Overview", "AI Analysis", "Evidence", "Recommendation", "Human Decision", "History"])
        with tabs[0]:
            self.overview(case)
            self.photo_evidence(case)
            self.duplicates(case)
        with tabs[1]:
            self.analysis(case)
        with tabs[2]:
            self.evidence(case)
        with tabs[3]:
            self.recommendation(case)
        with tabs[4]:
            self.human_decision(case)
        with tabs[5]:
            timeline(case.get("history", []), current=case["status"])
            with st.expander("Internal action notes"):
                for event in case.get("history", []):
                    field(label(event.get("event")), event.get("actor"))
                    if event.get("note"):
                        st.text(event["note"])

    @staticmethod
    def overview(case):
        st.subheader("Citizen report")
        st.text(case["text"])
        cols = st.columns(2)
        with cols[0]:
            field("Location type", case.get("location_context"))
            field("Public area / landmark", case.get("area"))
            field("Submitted", timestamp(case.get("submitted_at")))
        with cols[1]:
            field("Operational priority", label(case.get("human_priority") or (case.get("decision") or {}).get("priority")))
            field("Review urgency", label(case.get("review_urgency", "normal")))
            field("Processing mode", {"mock_demo": "Demo · synthetic outputs", "live": "Live", "unknown": "Not recorded"}.get(case.get("processing_mode"), "Not recorded"))
        if case.get("clarification_answers"):
            field("Reporter-supplied duration", case["clarification_answers"].get("duration"))
            field("Reporter hazard observations", case["clarification_answers"].get("hazards"))

    def photo_evidence(self, case):
        photo = case.get("photo")
        st.subheader("Photo Evidence")
        if not photo:
            st.caption("No photo was supplied with this complaint.")
            return
        try:
            image_bytes = self.api(
                "GET",
                f"/staff/complaints/{case['id']}/photo",
                protected=True,
                raw=True,
            )
            st.image(image_bytes, caption="Citizen-supplied photo evidence", width="stretch")
        except Exception:
            st.warning("The stored photo could not be displayed. Review the remaining case evidence.")

        st.caption("AI Image Analysis · advisory only. Staff must verify visible conditions before acting.")
        analysis = photo.get("analysis") or {}
        if not analysis:
            st.info("Automated image analysis is not available. The photo can still be reviewed manually.")
            return
        field("Visible waste types", ", ".join(analysis.get("visible_waste_types", [])) or "Not identified")
        field("Possible visible hazards", ", ".join(analysis.get("visible_hazards", [])) or "None identified")
        field("Scene summary", analysis.get("scene_summary") or "Not available")
        field("Severity hint", label(analysis.get("severity_hint")))
        confidence = analysis.get("confidence")
        field("Model-reported confidence", f"{confidence:.0%}" if confidence is not None else "Not available")
        st.caption("Image confidence is model-reported and is not a calibrated probability.")
        if analysis.get("image_text_conflict"):
            st.warning("Reporter information and AI image observations may conflict. Human review is required.")
        for note in analysis.get("uncertainty_notes", []):
            st.info(note)
        for reason in analysis.get("review_reasons", []):
            st.warning(reason)

    @staticmethod
    def analysis(case):
        data = case.get("analysis")
        st.subheader("AI Analysis")
        if not data:
            empty_state("Analysis is not available yet", "The report is saved. Staff can still handle the case manually after processing fails.")
            return
        for name, value in [("Waste types", ", ".join(data.get("waste_types", []))),
                ("Location", data.get("location")), ("Duration", f"{data['duration_days']} days" if data.get("duration_days") is not None else "Unknown"),
                ("Severity", label(data.get("severity"))), ("Issue type", data.get("issue_type")), ("Summary", data.get("summary"))]:
            field(name, value)
        with st.expander("Technical JSON · analysis"):
            st.json(data)

    @staticmethod
    def evidence(case):
        data = case.get("retrieval") or {}
        st.subheader("Supporting Evidence")
        available = data.get("evidence_available")
        st.write("Evidence available: " + ("Yes" if available is True else "No" if available is False else "Not recorded"))
        field("Grounded", "Yes" if data.get("grounded") is True else "No" if data.get("grounded") is False else "Not recorded")
        st.caption("Grounded means retrieved evidence was available and used. It does not mean every generated claim has been independently verified.")
        field("Claim verification", label(data.get("claim_verification")) if data.get("claim_verification") else "Not recorded")
        st.caption("Similarity measures semantic relatedness. It is not a probability that the information is correct.")
        if data.get("answer"):
            field("Evidence-based AI summary", data["answer"])
        for issue in (data.get("citation_validation") or {}).get("issues", []):
            st.warning(issue)
        if not data.get("evidence"):
            empty_state("No supporting passages available", "Use staff judgment; no claim is independently verified by this screen.")
        for number, item in enumerate(data.get("evidence", []), 1):
            evidence_card(number, item)

    @staticmethod
    def recommendation(case):
        decision = case.get("decision") or {}
        st.subheader("AI Recommendation")
        st.info("Advisory only. Record the operational decision in Human Decision.")
        if not decision:
            empty_state("No automated recommendation", "Available analysis and evidence remain visible in their tabs.")
            return
        field("Priority", label(decision.get("priority")))
        field("Review urgency", label(case.get("review_urgency", "normal")))
        required = decision.get("requires_human_review")
        field("Human review required", "Yes" if required is True else "No" if required is False else "Not recorded")
        field("Recommended action", decision.get("recommended_action"))
        field("Explanation", decision.get("explanation"))
        confidence = decision.get("confidence")
        field("Model-reported confidence", f"{confidence:.0%}" if confidence is not None else "Not available")
        st.caption("Not a calibrated probability.")
        st.caption("Sources cited by the recommendation")
        sources = {item["source"]: item for item in (case.get("retrieval") or {}).get("sources", [])}
        for source in decision.get("supporting_sources", []):
            st.text(sources.get(source, {}).get("title") or source)
        if not decision.get("supporting_sources"):
            st.text("No supporting sources cited.")
        for question in decision.get("clarification_questions", []):
            st.text("Clarification needed: " + question)
        issues = [*(decision.get("validation") or {}).get("issues", []), *(case.get("validation") or {}).get("warnings", [])]
        for issue in dict.fromkeys(issues):
            st.warning(issue)

    def human_decision(self, case):
        st.subheader("Human Decision")
        st.write("AI output is advisory. This staff decision controls the operational case.")
        if case.get("reviewer"):
            with st.container(border=True):
                field("Decision", label(case.get("review_decision")))
                field("Reviewed by", case["reviewer"])
                field("Reviewed at", timestamp(case.get("reviewed_at")))
                field("Reason", case.get("review_reason"))
                field("Human priority", label(case.get("human_priority")))
                field("Human action", case.get("human_action"))
        if case["status"] in {"awaiting_review", "processing_failed"}:
            st.subheader("Human Review Required")
            options = ["Override recommendation"] if case["status"] == "processing_failed" or not case.get("decision") else ["Approve recommendation", "Override recommendation"]
            choice = st.radio("Review decision", options, key="case_review_choice_" + case["id"])
            override = choice == "Override recommendation"
            with st.form("case_review_" + case["id"]):
                reason = st.text_area("Review reason", max_chars=2000, key="case_reason_" + case["id"])
                priority, action = None, None
                if override:
                    priority = st.selectbox("Priority for human decision", PRIORITIES, format_func=label, key="case_priority_" + case["id"])
                    action = st.text_area("Recommended action for human decision", max_chars=2000, key="case_action_" + case["id"])
                confirm = st.checkbox("I have reviewed the available evidence and confirm this decision.", key="case_confirm_review_" + case["id"])
                send = st.form_submit_button("Save Human Decision", type="primary")
            if send:
                if len(reason.strip()) < 3 or (override and len((action or "").strip()) < 3):
                    st.warning("Add a review reason and, when overriding, a concrete action (at least three characters each).")
                elif not confirm:
                    st.warning("Confirm that you have reviewed the case before saving.")
                else:
                    self.change(case, "review", {"decision": "override" if override else "approve", "reason": reason.strip(),
                        "priority": priority, "action": action.strip() if action else None})
        if case["status"] == "reviewed":
            with st.form("case_assign_" + case["id"]):
                st.subheader("Assignment")
                assignee = st.text_input("Assign to team / assignee", max_chars=120, key="case_assignee_" + case["id"])
                send = st.form_submit_button("Assign Complaint", type="primary")
            if send:
                if len(assignee.strip()) < 2:
                    st.warning("Enter a team or assignee with at least two characters.")
                else:
                    self.change(case, "assign", {"assignee": assignee.strip()})
        if case.get("assignee"):
            field("Assigned to", case["assignee"])
        if case["status"] == "assigned":
            with st.form("case_resolve_" + case["id"]):
                st.subheader("Resolution")
                note = st.text_area("Resolution note (staff only)", max_chars=2000, key="case_note_" + case["id"])
                confirm = st.checkbox("I confirm the reported issue has been resolved.", key="case_confirm_resolve_" + case["id"])
                send = st.form_submit_button("Mark Resolved", type="primary")
            if send:
                if len(note.strip()) < 3 or not confirm:
                    st.warning("Add a resolution note and confirm that the issue is resolved.")
                else:
                    self.change(case, "resolve", {"note": note.strip()})
        if case["status"] == "resolved":
            st.success("This complaint has been resolved.")
            field("Resolution note · staff only", case.get("resolution_note"))
            field("Resolved", timestamp(case.get("resolved_at")))
        if case["status"] in {"processing_failed", "processing"}:
            st.caption("Retry is available for failed or interrupted processing. The service prevents duplicate active runs and enforces retry limits.")
            if st.button("Retry Processing"):
                with st.spinner("Retrying automated processing..."):
                    self.change(case, "retry", {})

    def duplicates(self, case):
        with st.expander("Possible duplicate incidents"):
            st.caption("SmartWaste only suggests possible duplicates. Staff must confirm. Linking retains both original reports.")
            key = "duplicates_" + case["id"]
            if st.button("Find Possible Duplicates"):
                st.session_state[key] = self.get(f"/staff/complaints/{case['id']}/duplicates")
            data = st.session_state.get(key)
            if data is None:
                return
            if data.get("reason"):
                st.text(data["reason"])
            if not data.get("suggestions"):
                empty_state("No likely duplicate reports were found." if data.get("available", True) else "Suggestions are unavailable.",
                            "You can continue reviewing this complaint independently.")
            for candidate in data.get("suggestions", []):
                with st.container(border=True):
                    st.write("Possible duplicate")
                    field("Tracking ID", candidate["tracking_id"])
                    field("Shared reporter-supplied area", case.get("area"))
                    field("Text similarity", f"{candidate['similarity']:.3f}")
                    st.text(candidate["reason"])
                    with st.form("duplicate_form_" + case["id"] + "_" + candidate["id"]):
                        reason = st.text_input("Why are these the same incident?", max_chars=1000)
                        send = st.form_submit_button("Confirm Duplicate Link")
                    if send:
                        if len(reason.strip()) < 3:
                            st.warning("Add a reason with at least three characters before confirming the link.")
                        else:
                            self.change(case, "duplicate", {"other_id": candidate["id"], "reason": reason.strip()})
            if data.get("confirmed_links"):
                st.caption(f"Confirmed links: {len(data['confirmed_links'])}. Both original submissions are retained.")
                for link in data["confirmed_links"]:
                    field("Confirmed by", link.get("confirmed_by"))
                    field("Reason", link.get("reason"))


def staff_portal(api):
    portal = StaffPortal(api)
    # Only API errors are handled by the caller; programming failures must remain visible to tests.
    portal.render()
