import unittest
from agents.decision.triage import hazard_mentions, clarification_questions
from agents.decision.rules import validate_decision
from backend.schemas import AnalysisResult, DecisionResult, RetrievalResult
from backend.services.validator import validate


class TriageTests(unittest.TestCase):
    def test_hazard_denial_and_ambiguity(self):
        self.assertEqual(hazard_mentions("Not hazardous. No syringes. Not chemical waste."), (False, False))
        self.assertEqual(hazard_mentions("Chemical containers and syringes present."), (True, False))
        self.assertEqual(hazard_mentions("I am not sure if it is chemical waste."), (False, True))
        self.assertEqual(hazard_mentions("Not hazardous, but syringes are present."), (True, False))
        self.assertEqual(hazard_mentions("Not only chemical waste is present."), (True, False))

    def test_urgent_review_for_high_severity_even_with_low_priority(self):
        analysis = AnalysisResult(waste_types=["mixed"], severity="high")
        decision = DecisionResult(priority="low", recommended_action="Inspect", confidence=0.9, requires_human_review=False)
        retrieval = RetrievalResult(query="waste", answer="", grounded=False)
        validate(analysis, retrieval, decision)
        self.assertTrue(decision.requires_human_review)
        self.assertEqual(decision.review_urgency, "urgent")
        self.assertEqual(decision.priority.value, "low")
        self.assertTrue(decision.clarification_questions)

    def test_complete_routine_information_does_not_require_clarification(self):
        self.assertEqual(clarification_questions({"location": "street", "duration_days": 2, "waste_types": ["household"]}), [])
