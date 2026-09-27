import unittest
from unittest.mock import patch
from tests import test_workflow
from backend.services.dashboard import summary
from backend.repositories import complaints as repo
from backend.database import connection
from backend.config import settings


class DashboardTests(unittest.TestCase):
    setUp = test_workflow.WorkflowTests.setUp

    def test_counts_empty_and_resolution_durations_from_actual_rows(self):
        self.assertEqual(summary()["total"], 0)
        self.assertIsNone(summary()["median_resolution_hours"])
        with patch.object(settings, "use_mock_agents", True):
            first,_ = repo.create("Synthetic complaint one", None, area="Market")
            second,_ = repo.create("Synthetic complaint two", None, area="Market")
        repo.update(first["id"], {"status":"resolved","resolved_at":"2026-01-01T02:00:00+00:00"})
        with connection() as db:
            db.execute("UPDATE complaints SET submitted_at='2026-01-01T00:00:00+00:00'")
        self.assertIsNone(summary()["average_resolution_hours"])
        repo.update(second["id"], {"status":"resolved","resolved_at":"2026-01-01T04:00:00+00:00"})
        result = summary()
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["median_resolution_hours"], 3)
        self.assertEqual(result["average_resolution_hours"], 3)
        self.assertEqual(result["record_modes"], {"mock_demo":2})
        self.assertEqual(result["by_area"], {"Market":2})
