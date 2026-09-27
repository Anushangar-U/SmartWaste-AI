import unittest
from unittest.mock import patch
from tests import test_auth_api, test_workflow
from backend.middleware import resources
from backend.config import settings
from backend.repositories import complaints as repo
from backend.services import cases
from backend.maintenance import retention


class ResourceTests(unittest.TestCase):
    setUp = test_auth_api.AuthApiTests.setUp

    def test_rate_and_input_limits(self):
        resources._requests.clear()
        with patch.object(settings, "public_requests_per_minute", 1):
            payload = {"text": "Household garbage remains for two days."}
            self.assertEqual(self.client.post("/complaints", json=payload).status_code, 201)
            self.assertEqual(self.client.post("/complaints", json=payload).status_code, 429)
        resources._requests.clear()
        self.assertEqual(self.client.post("/complaints", json={"text":" "*20}).status_code, 422)
        self.assertEqual(self.client.post("/complaints", content=b"x"*20000).status_code, 413)

    def test_correlation_and_safe_tracking_log(self):
        resources._requests.clear()
        with self.assertLogs("smartwaste", level="INFO") as logs:
            reply = self.client.post("/complaints", json={"text":"Household garbage remains for two days."})
            tracked = self.client.get("/complaints/track/"+reply.json()["tracking_id"])
        rid = reply.headers["X-Request-ID"]
        self.assertTrue(any("stage=analyst" in item and rid in item for item in logs.output))
        self.assertNotIn(reply.json()["tracking_id"], " ".join(logs.output))
        self.assertEqual(tracked.status_code, 200)


class RetentionConcurrencyTests(unittest.TestCase):
    setUp = test_workflow.WorkflowTests.setUp

    def test_capacity_preserves_record_and_retention_only_deletes_old_resolved(self):
        with patch.object(settings, "max_concurrent_processing", 1), resources.processing_slot() as admitted:
            self.assertTrue(admitted)
            case,_ = cases.submit("Household garbage awaiting processing.")
        self.assertEqual(case["error_stage"], "capacity")
        old,_ = repo.create("Synthetic expired resolved complaint", None)
        repo.update(old["id"], {"status":"resolved", "resolved_at":"2000-01-01T00:00:00+00:00"})
        with patch.object(settings, "retention_days", 90):
            self.assertEqual(retention()["deleted"], 0)
            self.assertEqual(retention(True)["deleted"], 1)
        self.assertIsNotNone(repo.get(case["id"]))
        self.assertIsNone(repo.get(old["id"]))
