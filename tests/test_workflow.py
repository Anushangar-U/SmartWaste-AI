import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from backend.config import settings
from backend.database import initialize
from backend.repositories import complaints as repo
from backend.services import cases
from backend.services.orchestrator import AgentError
from backend.api.complaint_routes import ReviewRequest, AssignmentRequest, ResolutionRequest, assign, resolve


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = patch.object(settings, "database_path", str(Path(self.tmp.name) / "test.sqlite3"))
        self.cfg.start()
        self.addCleanup(self.cfg.stop)
        initialize()

    def submit(self):
        with patch.object(settings, "use_mock_agents", True):
            return cases.submit("Household garbage uncollected for two days.", "Residential street", "a" * 32)[0]

    def test_persistence_idempotency_and_private_tracking(self):
        case = self.submit()
        initialize()  # Fresh connections and repeat startup retain data.
        self.assertEqual(repo.track(case["tracking_id"])["id"], case["id"])
        repeated = self.submit()
        self.assertEqual(case["id"], repeated["id"])
        self.assertEqual(len(repo.list_cases()), 1)
        public = cases.public_status(case)
        for private in ["text", "analysis", "review_reason", "reviewer", "idempotency_key"]:
            self.assertNotIn(private, public)
        with self.assertRaises(repo.Conflict):
            cases.submit("Different complaint body", None, "a" * 32)

    def test_review_assign_resolve_and_stale_transition(self):
        case = self.submit()
        review = ReviewRequest(version=case["version"], decision="approve", reason="Evidence checked")
        reviewed = cases.review(case, review, "reviewer")
        with self.assertRaises(repo.Conflict):
            cases.review(case, review, "reviewer")
        assigned = assign(case["id"], AssignmentRequest(version=reviewed["version"], assignee="Team A"), {"username": "reviewer"})
        resolved = resolve(case["id"], ResolutionRequest(version=assigned["version"], note="Collection confirmed"), {"username": "reviewer"})
        self.assertEqual(cases.public_status(resolved)["status"], "resolved")
        self.assertEqual(resolved["reviewer"], "reviewer")
        self.assertTrue(resolved["resolved_at"])
        with self.assertRaises(repo.Conflict):
            assign(case["id"], AssignmentRequest(version=resolved["version"], assignee="Team B"), {"username": "reviewer"})

    def test_provider_failure_keeps_submission(self):
        with patch.object(cases, "process_complaint", side_effect=AgentError("analyst")):
            case, _ = cases.submit("A synthetic complaint for failure testing.")
        self.assertEqual(case["status"], "processing_failed")
        self.assertEqual(repo.track(case["tracking_id"])["error_stage"], "analyst")
        self.assertNotIn("error_stage", cases.public_status(case))


if __name__ == "__main__":
    unittest.main()
