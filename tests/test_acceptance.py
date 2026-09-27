import unittest
from tests import test_auth_api
from backend.auth import users, security
from backend.database import initialize


class AcceptanceTests(unittest.TestCase):
    setUp = test_auth_api.AuthApiTests.setUp

    def test_complete_http_lifecycle_and_public_privacy(self):
        users.create_user("case_worker", "synthetic-password", "staff")
        auth = {"Authorization": "Bearer " + security.create_access_token("case_worker", "staff")}
        payload = {"text": "Household garbage has remained uncollected for two days.", "area": "Market north gate"}
        key = {"Idempotency-Key": "synthetic-idempotency-key"}
        receipt = self.client.post("/complaints", json=payload, headers=key).json()
        duplicate = self.client.post("/complaints", json=payload, headers=key).json()
        self.assertEqual(receipt["tracking_id"], duplicate["tracking_id"])
        queue = self.client.get("/staff/complaints", headers=auth).json()
        self.assertEqual(len(queue), 1)
        case = queue[0]
        base = "/staff/complaints/" + case["id"]
        reviewed = self.client.post(base + "/review", headers=auth,
            json={"version":case["version"],"decision":"override","reason":"Private staff reason", "priority":"low","action":"Arrange routine collection"})
        self.assertEqual(reviewed.status_code, 200)
        assigned = self.client.post(base + "/assign", headers=auth,
            json={"version":reviewed.json()["version"], "assignee":"Collection team"})
        self.assertEqual(assigned.status_code, 200)
        resolved = self.client.post(base + "/resolve", headers=auth,
            json={"version":assigned.json()["version"], "note":"Private resolution detail"})
        self.assertEqual(resolved.status_code, 200)
        initialize()
        public = self.client.get("/complaints/track/" + receipt["tracking_id"])
        self.assertEqual(public.json()["status"], "resolved")
        for private in ["Private staff reason", "Private resolution detail", "case_worker", payload["text"]]:
            self.assertNotIn(private, public.text)
        self.assertEqual(self.client.post(base + "/resolve", headers=auth,
            json={"version":resolved.json()["version"],"note":"Repeat resolution"}).status_code, 409)
        self.assertEqual(self.client.get("/staff/dashboard").status_code, 401)
