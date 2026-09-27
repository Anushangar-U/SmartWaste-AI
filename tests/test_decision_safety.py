import unittest

from agents.decision.rules import validate_decision
from backend.schemas import AnalysisResult, DecisionResult, RetrievalResult
from backend.services.validator import validate


def decision(**changes):
    result = {
        "priority": "medium",
        "recommended_action": "Schedule collection.",
        "explanation": "Routine collection is appropriate.",
        "supporting_sources": ["guide.pdf"],
        "requires_human_review": False,
        "confidence": 0.85,
    }
    result.update(changes)
    return result


EVIDENCE = [{"source": "guide.pdf", "text": "General collection guidance."}]


class DecisionSafetyTests(unittest.TestCase):
    def test_generated_hazard_words_do_not_flag_routine_complaint(self):
        result, issues = validate_decision(
            decision(
                explanation="No hazardous or medical material is reported.",
                recommended_action="Use normal collection, not a chemical team.",
            ),
            EVIDENCE + [{"source": "hazard.pdf", "text": "Medical waste guidance."}],
            analysis={
                "waste_types": ["household"],
                "issue_type": "uncollected garbage",
                "summary": "Household garbage has not been collected for two days.",
            },
            complaint_text="Household garbage has not been collected from a residential street for two days.",
        )
        self.assertFalse(result["requires_human_review"])
        self.assertFalse(any("High-risk keyword" in issue for issue in issues))

    def test_original_hazardous_complaint_requires_review(self):
        result, issues = validate_decision(
            decision(),
            EVIDENCE,
            analysis={"waste_types": ["mixed"], "issue_type": "dumping", "summary": "Waste was dumped."},
            complaint_text=(
                "Several leaking chemical containers and used syringes have "
                "been dumped beside a school near the river since yesterday."
            ),
        )
        self.assertTrue(result["requires_human_review"])
        self.assertEqual(sum("High-risk keyword" in issue for issue in issues), 1)

    def test_analysis_risk_is_used_when_original_text_unavailable(self):
        result, issues = validate_decision(
            decision(), EVIDENCE, analysis={"waste_types": ["chemical"]}
        )
        self.assertTrue(result["requires_human_review"])
        self.assertTrue(any("High-risk keyword" in issue for issue in issues))

    def test_agent_failure_is_not_repeated_in_pipeline_warnings(self):
        analysis = AnalysisResult(
            waste_types=["plastic"], location="street", duration_days=2,
            severity="medium", issue_type="uncollected waste", summary="Plastic waste.",
        )
        retrieval = RetrievalResult(
            query="plastic waste", answer="Collection guidance.", grounded=True,
            sources=[{"source": "guide.pdf", "page": 2}],
            evidence=[{
                "chunk_id": "guide_2", "source": "guide.pdf", "page": 2,
                "text": "Collect waste.", "score": 0.8,
            }],
        )
        recommendation = DecisionResult(
            priority="medium", recommended_action="Schedule collection.",
            supporting_sources=["guide.pdf"], confidence=0.8,
            validation={"passed": False, "issues": ["High-risk keyword detected; forced human review."]},
        )
        report = validate(analysis, retrieval, recommendation)
        self.assertFalse(report.passed)
        self.assertTrue(recommendation.requires_human_review)
        self.assertEqual(report.warnings, [])
        self.assertEqual(len(recommendation.validation.issues), 1)

    def test_missing_evidence_has_one_visible_issue(self):
        analysis = AnalysisResult(
            waste_types=["plastic"], severity="medium", issue_type="uncollected waste"
        )
        retrieval = RetrievalResult(
            query="plastic waste", answer="No guidance.", grounded=False,
            sources=[], evidence=[],
        )
        recommendation = DecisionResult(
            priority="medium", recommended_action="Manual review required.",
            confidence=0.0,
            validation={"passed": False, "issues": ["No evidence was retrieved for this complaint."]},
        )
        report = validate(analysis, retrieval, recommendation)
        all_messages = recommendation.validation.issues + report.warnings
        self.assertEqual(sum("evidence" in message.lower() for message in all_messages), 1)
        self.assertFalse(report.passed)
        self.assertTrue(recommendation.requires_human_review)

    def test_malformed_decision_still_produces_safe_schema(self):
        result, issues = validate_decision(
            {"priority": ["urgent"], "supporting_sources": [{}], "confidence": "nan"},
            EVIDENCE,
        )
        self.assertTrue(issues)
        self.assertTrue(result["requires_human_review"])
        self.assertEqual(result["recommended_action"], "Manual review required.")
        self.assertEqual(result["confidence"], 0.0)
        DecisionResult.model_validate(result)

    def test_unsupported_citation_forces_review(self):
        result, issues = validate_decision(
            decision(supporting_sources=["invented.pdf"]), EVIDENCE
        )
        self.assertEqual(result["supporting_sources"], [])
        self.assertTrue(result["requires_human_review"])
        self.assertTrue(any("Removed cited sources" in issue for issue in issues))

    def test_empty_model_response_uses_parse_fallback(self):
        from agents.decision.agent import _extract_json

        with self.assertRaisesRegex(ValueError, "empty response"):
            _extract_json(None)


if __name__ == "__main__":
    unittest.main()
