import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "frontend/app.py")


def response(data, status=200):
    return SimpleNamespace(status_code=status, json=lambda: data)


class FrontendTests(unittest.TestCase):
    def test_citizen_submission_uses_backend_identifier(self):
        receipt = {"tracking_id": "WM-synthetic", "status": "awaiting_review", "history": []}
        with patch("requests.request", return_value=response(receipt)) as request:
            app = AppTest.from_file(APP).run()
            app.text_area[0].set_value("Household garbage has been left for two days.")
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.code[0].value, "WM-synthetic")
            self.assertTrue(request.call_args.kwargs["headers"]["Idempotency-Key"])

    def test_staff_reads_shared_backend_and_safe_plain_text(self):
        case = {"id": "test", "tracking_id": "WM-test", "text": "<script>alert(1)</script>",
            "status": "resolved", "submitted_at": "2026-01-01", "requires_human_review": False,
            "history": [], "version": 1}
        def request(method, url, **kwargs):
            return response([case] if url.endswith("/staff/complaints") else case)
        with patch("requests.request", side_effect=request) as calls:
            app = AppTest.from_file(APP).run()
            app.session_state["auth_token"] = "synthetic-test-token"
            app.sidebar.radio[0].set_value("Staff").run()
            self.assertFalse(app.exception)
            self.assertTrue(any(t.value == case["text"] for t in app.text))
            self.assertTrue(all(c.kwargs["headers"].get("Authorization") for c in calls.call_args_list))


if __name__ == "__main__":
    unittest.main()
