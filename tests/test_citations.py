import unittest
import pymupdf
from retrieval.citations import inspect_answer, verify_passage, sensitive_claim_issues
from retrieval.sources import ROOT


class CitationTests(unittest.TestCase):
    def test_real_pdf_passage_and_wrong_page_or_source(self):
        source = "sri_lanka_waste_policy.pdf"
        with pymupdf.open(ROOT / "documents" / source) as doc:
            passage = doc[0].get_text().strip()
        evidence = {"source": source, "page": 1, "text": passage}
        self.assertTrue(verify_passage(evidence))
        self.assertFalse(verify_passage({**evidence, "page": 9999}))
        self.assertFalse(verify_passage({**evidence, "text": "Invented passage not in PDF"}))
        self.assertFalse(verify_passage({**evidence, "source": "../.env"}))
        _, checks = inspect_answer("The source is a plastic waste action plan [1].", [evidence])
        self.assertTrue(checks["passed"])
        self.assertEqual(checks["claim_verification"], "not_independently_verified")

    def test_invalid_identifier_removed_and_sensitive_claim_review(self):
        text, check = inspect_answer("The law requires collection within 17 hours [9].", [{"text": "General guidance"}], verifier=lambda _: True)
        self.assertNotIn("[9]", text)
        self.assertFalse(check["passed"])
        self.assertEqual(check["invalid_citations"], [9])
        self.assertTrue(sensitive_claim_issues("Collect within 17 hours [1].", [{"text": "General guidance"}]))
        self.assertFalse(sensitive_claim_issues("Collect within 17 hours [1].", [{"text": "Fixture says 17 hours."}]))

    def test_missing_citation_is_not_verified(self):
        _, check = inspect_answer("Collect safely.", [], verifier=lambda _: True)
        self.assertFalse(check["passed"])
