import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.config import settings
from backend.main import app
from backend.database import connection, initialize
from backend.auth import users, security


class AuthApiTests(unittest.TestCase):
    def setUp(self):
        from backend.middleware import resources
        resources._requests.clear()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for target, value in [("database_path", str(Path(self.tmp.name) / "db.sqlite3")), ("admin_password", ""), ("use_mock_agents", True)]:
            p = patch.object(settings, target, value)
            p.start()
            self.addCleanup(p.stop)
        logging_patch = patch("backend.main.setup_logging")
        logging_patch.start()
        self.addCleanup(logging_patch.stop)
        self.client = TestClient(app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def header(self, username, role):
        users.create_user(username, "synthetic-password", role)
        return {"Authorization": "Bearer " + security.create_access_token(username, role)}

    def test_roles_and_all_staff_actions_require_auth(self):
        for method, path in [("get", "/staff/complaints"), ("get", "/staff/complaints/missing"),
            *(('post', '/staff/complaints/missing/' + action) for action in ['review','assign','resolve','retry'])]:
            self.assertEqual(getattr(self.client, method)(path).status_code, 401)
        normal = self.header("citizen", "user")
        self.assertEqual(self.client.get("/staff/complaints", headers=normal).status_code, 403)
        for role in ["admin", "staff"]:
            header = self.header(role, role)
            self.assertEqual(self.client.get("/staff/complaints", headers=header).status_code, 200)

    def test_disabled_missing_expired_and_demoted_accounts(self):
        header = self.header("worker", "staff")
        users.update_user("worker", "staff", "disabled")
        self.assertEqual(self.client.get("/staff/complaints", headers=header).status_code, 401)
        users.update_user("worker", "user", "active")
        self.assertEqual(self.client.get("/staff/complaints", headers=header).status_code, 403)
        with patch("backend.auth.security.datetime") as clock:
            clock.now.return_value = datetime.now(timezone.utc) - timedelta(days=7)
            expired = security.create_access_token("worker", "user")
        self.assertEqual(self.client.get("/staff/complaints", headers={"Authorization": "Bearer " + expired}).status_code, 401)
        with connection() as db:
            db.execute("DELETE FROM users WHERE username='worker'")
        self.assertEqual(self.client.get("/staff/complaints", headers=header).status_code, 401)

    def test_registration_persists_without_public_role_escalation(self):
        response = self.client.post("/auth/register", json={"username": "new_user", "password": "synthetic-password", "role": "admin"})
        self.assertEqual(response.status_code, 201)
        initialize()
        self.assertEqual(users.get_user("new_user")["role"], "user")
        self.assertEqual(self.client.post("/auth/login", data={"username": "new_user", "password": "synthetic-password"}).status_code, 200)
        self.assertEqual(self.client.post("/auth/register", json={"username": "another", "password": "\u0b85" * 30}).status_code, 422)

    def test_routine_processed_case_still_enters_staff_review_queue(self):
        reply = self.client.post(
            "/complaints",
            json={"text": "Household garbage uncollected for two days."},
        )
        self.assertEqual(reply.status_code, 201)
        case = repo.track(reply.json()["tracking_id"])
        self.assertEqual(case["status"], "awaiting_review")
        self.assertTrue(case["requires_human_review"])
        # Preserve the decision agent's separate safety-escalation meaning.
        self.assertFalse(case["decision"]["requires_human_review"])

        header = self.header("queue_reviewer", "staff")
        queue = self.client.get(
            "/staff/complaints",
            params={"review_needed": "true"},
            headers=header,
        )
        self.assertEqual(queue.status_code, 200)
        self.assertTrue(any(item["id"] == case["id"] for item in queue.json()))

    def test_separate_clients_share_persisted_tracking(self):
        reply = self.client.post("/complaints", json={"text": "Household garbage uncollected for two days."})
        self.assertEqual(reply.status_code, 201)
        tracking = reply.json()["tracking_id"]
        header = self.header("reviewer", "staff")
        other = TestClient(app)
        queue = other.get("/staff/complaints", headers=header).json()
        self.assertEqual(queue[0]["tracking_id"], tracking)
        case = queue[0]
        review = other.post(f'/staff/complaints/{case["id"]}/review', headers=header,
            json={"version": case["version"], "decision": "approve", "reason": "Checked evidence"})
        self.assertEqual(review.status_code, 200)
        self.assertEqual(self.client.get("/complaints/track/" + tracking).json()["status"], "reviewed")
        self.assertNotIn("review_reason", self.client.get("/complaints/track/" + tracking).json())


if __name__ == "__main__":
    unittest.main()
