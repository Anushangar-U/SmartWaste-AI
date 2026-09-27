import unittest
from tests import test_workflow
from backend.repositories import complaints as repo
from backend.services.duplicates import suggestions, confirm
from backend.database import connection


class DuplicateTests(unittest.TestCase):
    setUp = test_workflow.WorkflowTests.setUp

    def test_requires_explicit_area_and_retains_both_records(self):
        first,_ = repo.create("Overflowing bin at the market gate", "Commercial area", area="Central Market")
        second,_ = repo.create("The bin near the market gate is overflowing", "Commercial area", area="Central Market")
        other,_ = repo.create("The market bin is overflowing", "Commercial area", area="Different Market")
        result = suggestions(first, scorer=lambda texts: [0.95] * (len(texts)-1))
        self.assertEqual([s["id"] for s in result["suggestions"]], [second["id"]])
        confirm(first["id"], second["id"], "staff", "Same reported landmark and incident")
        self.assertEqual(len(repo.list_cases()), 3)
        self.assertEqual(repo.get(first["id"])["status"], "submitted")
        with self.assertRaises(repo.Conflict):
            confirm(second["id"], first["id"], "staff", "Again")
        no_area,_ = repo.create("Overflowing bin at a commercial area", "Commercial area")
        self.assertEqual(suggestions(no_area)["suggestions"], [])

    def test_old_reports_and_low_similarity_are_not_suggested(self):
        first,_ = repo.create("New waste complaint", None, area="Market")
        old,_ = repo.create("Old waste complaint", None, area="Market")
        with connection() as db:
            db.execute("UPDATE complaints SET submitted_at='2000-01-01T00:00:00+00:00' WHERE id=?", (old["id"],))
        self.assertEqual(suggestions(first, scorer=lambda _: [0.99])["suggestions"], [])
        repo.create("Unrelated issue at same area", None, area="Market")
        self.assertEqual(suggestions(first, scorer=lambda _: [0.1])["suggestions"], [])
