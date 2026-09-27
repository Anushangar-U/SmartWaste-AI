import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "frontend/app.py")


def response(data, status=200):
    return SimpleNamespace(status_code=status, json=lambda: data)


def widget(app, kind, label):
    return next(item for item in getattr(app, kind) if item.label == label)


def click(app, label):
    return widget(app, "button", label).click().run()


class FrontendTests(unittest.TestCase):
    def test_public_default_login_is_opt_in_and_demo_visible(self):
        with patch("requests.request", return_value=response({"mode": "mock_demo"})) as calls:
            app = AppTest.from_file(APP).run()
            self.assertFalse(app.exception)
            self.assertFalse(app.text_input)
            self.assertFalse(app.sidebar.radio)
            self.assertTrue(any(b.label == "Staff Login" for b in app.button))
            self.assertTrue(any("DEMO MODE" in w.value for w in app.warning))
            self.assertFalse(any(c.kwargs["headers"].get("Authorization") for c in calls.call_args_list))
            click(app, "Staff Login")
            self.assertEqual([t.label for t in app.text_input], ["Username", "Password"])
            click(app, "Back to Citizen Portal")
            self.assertFalse(app.text_input)

    def test_login_denial_clears_password_and_hides_private_workspace(self):
        with patch("requests.request", return_value=response({"mode": "mock_demo"})) as calls:
            app = AppTest.from_file(APP).run()
            click(app, "Staff Login")
            widget(app, "text_input", "Username").set_value("ordinary_user")
            widget(app, "text_input", "Password").set_value("synthetic-password")
            calls.return_value = response({"role": "user", "access_token": "synthetic-unused"})
            click(app, "Sign In")
            self.assertFalse(app.exception)
            self.assertEqual(widget(app, "text_input", "Password").value, "")
            self.assertNotIn("auth_token", app.session_state)
            self.assertTrue(any("not authorized" in e.value for e in app.error))

    def test_expired_session_clears_staff_data(self):
        with patch("requests.request", return_value=response({}, 401)):
            app = AppTest.from_file(APP).run()
            app.session_state["auth_token"] = "synthetic-expired"
            app.session_state["page"] = "staff"
            app.session_state["duplicates_test"] = {"private": "synthetic"}
            app.run()
            self.assertFalse(app.exception)
            self.assertNotIn("auth_token", app.session_state)
            self.assertNotIn("duplicates_test", app.session_state)
            self.assertTrue(any(t.label == "Password" for t in app.text_input))

    def test_tracking_is_separate_and_only_recorded_history_is_shown(self):
        record = {"tracking_id": "WM-synthetic", "status": "processing_failed", "mode": "live",
            "history": [{"status": "submitted", "at": "2026-01-01T00:00:00+00:00"},
                        {"status": "processing_failed", "at": "2026-01-01T00:00:01+00:00"}]}
        with patch("requests.request", return_value=response(record)):
            app = AppTest.from_file(APP).run()
            app.button(key="nav_track").click().run()
            self.assertFalse(app.text_area)
            widget(app, "text_input", "Tracking ID").set_value("WM-synthetic")
            click(app, "Check Status")
            self.assertFalse(app.exception)
            history = next(m.value for m in app.markdown if "sw-timeline" in m.value and "<ol" in m.value)
            self.assertIn("Submitted", history)
            self.assertIn("Processing Incomplete", history)
            self.assertNotIn("Resolved", history)
            self.assertTrue(any("still saved" in w.value for w in app.warning))

    def test_submission_retry_reuses_idempotency_key(self):
        import requests
        payloads = []
        def request(method, url, **kwargs):
            if method == "POST":
                payloads.append(kwargs)
                if len(payloads) == 1:
                    raise requests.ConnectionError("Synthetic private provider message")
                return response({"tracking_id": "WM-synthetic", "status": "awaiting_review", "history": []})
            return response({"mode": "mock_demo"})
        with patch("requests.request", side_effect=request):
            app = AppTest.from_file(APP).run()
            click(app, "Report an Issue")
            app.text_area[0].set_value("Synthetic household waste has not been collected.")
            click(app, "Submit Complaint")
            self.assertNotIn("Synthetic private provider message", str([e.value for e in app.error]))
            click(app, "Submit Complaint")
            self.assertEqual(payloads[0]["headers"]["Idempotency-Key"], payloads[1]["headers"]["Idempotency-Key"])
            self.assertEqual(app.code[0].value, "WM-synthetic")

    def test_citizen_submission_uses_backend_identifier(self):
        receipt = {"tracking_id": "WM-synthetic", "status": "awaiting_review", "history": []}
        with patch("requests.request", return_value=response(receipt)) as request:
            app = AppTest.from_file(APP).run()
            next(b for b in app.button if b.label == "Report an Issue").click().run()
            app.text_area[0].set_value("Household garbage has been left for two days.")
            next(b for b in app.button if b.label == "Submit Complaint").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.code[0].value, "WM-synthetic")
            submission = next(c for c in request.call_args_list if c.args[0] == "POST")
            self.assertTrue(submission.kwargs["headers"]["Idempotency-Key"])

    def test_staff_reads_shared_backend_and_safe_plain_text(self):
        case = {"id": "test", "tracking_id": "WM-test", "text": "<script>alert(1)</script>",
            "status": "resolved", "submitted_at": "2026-01-01", "requires_human_review": False,
            "history": [], "version": 1}
        def request(method, url, **kwargs):
            if url.endswith("/staff/dashboard"):
                return response({"total":1,"review_backlog":0,"by_status":{"resolved":1},"record_modes":{"mock_demo":1},
                    "by_priority":{},"by_area":{},"average_resolution_hours":None})
            return response([case] if url.endswith("/staff/complaints") else case)
        with patch("requests.request", side_effect=request) as calls:
            app = AppTest.from_file(APP).run()
            app.session_state["auth_token"] = "synthetic-test-token"
            app.session_state["page"] = "staff"
            app.session_state["staff_case_id"] = "test"
            app.run()
            self.assertFalse(app.exception)
            self.assertTrue(any(t.value == case["text"] for t in app.text))
            self.assertFalse(any(case["text"] in m.value for m in app.markdown))
            self.assertTrue(all(c.kwargs["headers"].get("Authorization") for c in calls.call_args_list if "/staff/" in c.args[1]))


class FrontendJourneyTests(unittest.TestCase):
    """Two independent Streamlit sessions against the real API and an isolated DB."""
    def setUp(self):
        from tests.test_auth_api import AuthApiTests
        from backend.auth import users
        AuthApiTests.setUp(self)
        users.create_user("ui_worker", "synthetic-password", "staff")
        def bridge(method, url, **kwargs):
            from urllib.parse import urlsplit
            kwargs.pop("timeout", None)
            return self.client.request(method, urlsplit(url).path, **kwargs)
        self.requests = patch("requests.request", side_effect=bridge)
        self.calls = self.requests.start()
        self.addCleanup(self.requests.stop)

    def staff_app(self):
        app = AppTest.from_file(APP).run()
        click(app, "Staff Login")
        widget(app, "text_input", "Username").set_value("ui_worker")
        widget(app, "text_input", "Password").set_value("synthetic-password")
        click(app, "Sign In")
        self.assertFalse(app.exception)
        if "login_password" in app.session_state:
            self.assertEqual(app.session_state["login_password"], "")
        return app

    def submit_case(self):
        from backend.services import cases
        return cases.submit("Household garbage uncollected for three days.", "Residential street", area="Library gate")[0]

    def test_citizen_staff_review_assign_resolve_and_track(self):
        citizen = AppTest.from_file(APP).run()
        click(citizen, "Report an Issue")
        citizen.text_area[0].set_value("Household garbage uncollected for three days.")
        widget(citizen, "selectbox", "Location type").set_value("Residential street")
        widget(citizen, "text_input", "Public area / landmark (optional)").set_value("Library gate")
        widget(citizen, "text_input", "How long has it been there? (optional)").set_value("Three days")
        widget(citizen, "selectbox", "Hazards visible?").set_value("None observed")
        click(citizen, "Submit Complaint")
        self.assertFalse(citizen.exception)
        tracking = citizen.code[0].value
        staff = self.staff_app()
        self.assertEqual(staff.metric[0].value, "1")
        click(staff, "Open Complaints")
        self.assertTrue(any(tracking in t.value for t in staff.text))
        click(staff, "Open Case")
        self.assertFalse(staff.exception)
        self.assertEqual(len(staff.tabs), 6)
        self.assertTrue(any("Model-reported confidence" in c.value for c in staff.caption))
        widget(staff, "text_area", "Review reason").set_value("Evidence reviewed by authorized staff")
        widget(staff, "checkbox", "I have reviewed the available evidence and confirm this decision.").check()
        click(staff, "Save Human Decision")
        self.assertFalse(staff.exception)
        widget(staff, "text_input", "Assign to team / assignee").set_value("Collection team A")
        click(staff, "Assign Complaint")
        widget(staff, "text_area", "Resolution note (staff only)").set_value("Private note: collection completed")
        click(staff, "Mark Resolved")
        self.assertTrue(any("confirm" in w.value for w in staff.warning))
        widget(staff, "checkbox", "I confirm the reported issue has been resolved.").check()
        click(staff, "Mark Resolved")
        self.assertFalse(staff.exception)
        click(citizen, "Track this complaint")
        click(citizen, "Check Status")
        self.assertFalse(citizen.exception)
        self.assertTrue(any("Resolved" in m.value for m in citizen.markdown))
        self.assertNotIn("Private note", str([t.value for t in citizen.text]))
        click(staff, "Logout")
        self.assertNotIn("auth_token", staff.session_state)
        self.assertFalse(staff.text_input)
        self.assertTrue(any(b.label == "Staff Login" for b in staff.button))

    def test_stale_review_uses_original_version_until_refresh(self):
        from backend.repositories import complaints as repo
        case = self.submit_case()
        app = self.staff_app()
        click(app, "Open Complaints")
        click(app, "Open Case")
        repo.update(case["id"], {"review_urgency": "elevated"})
        widget(app, "text_area", "Review reason").set_value("Checked the old case")
        widget(app, "checkbox", "I have reviewed the available evidence and confirm this decision.").check()
        click(app, "Save Human Decision")
        self.assertFalse(app.exception)
        self.assertTrue(any("changed" in e.value for e in app.error))
        self.assertEqual(repo.get(case["id"])["status"], "awaiting_review")
        click(app, "Refresh Case")
        self.assertFalse(app.exception)
        self.assertEqual(widget(app, "text_area", "Review reason").value, "")
        self.assertFalse(widget(app, "checkbox", "I have reviewed the available evidence and confirm this decision.").value)

    def test_failure_retry_and_manual_override(self):
        from backend.repositories import complaints as repo
        from backend.services.orchestrator import AgentError
        from backend.services import cases
        with patch.object(cases, "process_complaint", side_effect=AgentError("analyst")):
            failed, _ = cases.submit("Synthetic report for a failed processing check")
        app = self.staff_app()
        click(app, "Open Complaints")
        click(app, "Open Case")
        self.assertEqual(widget(app, "radio", "Review decision").options, ["Override recommendation"])
        click(app, "Retry Processing")
        self.assertFalse(app.exception)
        self.assertEqual(repo.get(failed["id"])["status"], "awaiting_review")
        widget(app, "radio", "Review decision").set_value("Override recommendation").run()
        widget(app, "text_area", "Review reason").set_value("Staff chose a specific response")
        widget(app, "text_area", "Recommended action for human decision").set_value("Arrange collection after inspection")
        widget(app, "checkbox", "I have reviewed the available evidence and confirm this decision.").check()
        click(app, "Save Human Decision")
        self.assertEqual(repo.get(failed["id"])["review_decision"], "override")

    def test_duplicate_link_preserves_reports(self):
        from backend.services import cases
        from backend.repositories import complaints as repo
        self.submit_case()
        cases.submit("Household garbage by the same library gate.", "Residential street", area="Library gate")
        app = self.staff_app()
        click(app, "Open Complaints")
        next(b for b in app.button if b.label == "Open Case").click().run()
        with patch("backend.services.duplicates.semantic_scores", return_value=[0.95]):
            click(app, "Find Possible Duplicates")
        widget(app, "text_input", "Why are these the same incident?").set_value("Same landmark and observed waste")
        click(app, "Confirm Duplicate Link")
        self.assertFalse(app.exception)
        self.assertEqual(len(repo.list_cases()), 2)
        self.assertTrue(any("Both original" in s.value for s in app.success))

    def test_empty_dashboard_and_queue_filters(self):
        app = self.staff_app()
        self.assertEqual(app.metric[0].value, "0")
        self.assertTrue(any("No resolved cases yet" in c.value for c in app.caption))
        click(app, "Review waiting cases")
        self.assertTrue(any("No complaints currently require review" in m.value for m in app.markdown))
        self.submit_case()
        app.session_state["staff_view"] = "Assigned"
        app.run()
        listing = [c for c in self.calls.call_args_list if c.args[1].endswith("/staff/complaints")][-1]
        self.assertEqual(listing.kwargs["params"]["status"], "assigned")


if __name__ == "__main__":
    unittest.main()
