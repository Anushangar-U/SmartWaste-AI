from unittest.mock import patch
import unittest
from tests import test_workflow
from backend.config import settings
from backend.repositories import complaints as repo
from backend.services import cases, agent_client


class ResilienceTests(unittest.TestCase):
    setUp = test_workflow.WorkflowTests.setUp

    def test_hazard_review_urgency_survives_analyst_failure(self):
        with patch.object(agent_client, "call_analyst", side_effect=TimeoutError("private")):
            case,_ = cases.submit("Chemical containers and used syringes are dumped near the school.")
        self.assertEqual(case["status"], "processing_failed")
        self.assertEqual(case["review_urgency"], "urgent")
    def test_partial_result_and_resume_without_duplicate_analysis(self):
        with patch.object(settings, "use_mock_agents", True), patch.object(agent_client, "call_retrieval", side_effect=TimeoutError("private-provider-message")):
            case, _ = cases.submit("Household waste has not been collected for two days.")
        self.assertEqual(case["status"], "processing_failed")
        self.assertIsNotNone(case["analysis"])
        self.assertIsNone(case["retrieval"])
        self.assertEqual(case["error_stage"], "retrieval")
        self.assertNotIn("private-provider-message", str(case))
        with patch.object(settings, "use_mock_agents", True), patch.object(agent_client, "call_analyst", side_effect=AssertionError("analysis must be reused")):
            result = cases.process(case)
        self.assertEqual(result["status"], "awaiting_review")
        self.assertEqual(result["id"], case["id"])

    def test_retry_limit_and_live_processing_conflict(self):
        case, _ = repo.create("Test complaint for the processing lease.", None)
        active = repo.update(case["id"], {"status": "processing", "processing_started_at": repo.now()})
        with self.assertRaises(repo.Conflict):
            cases.process(active)
        failed = repo.update(case["id"], {"status": "processing_failed", "processing_attempts": settings.processing_max_attempts})
        with self.assertRaises(repo.Conflict):
            cases.process(failed)
