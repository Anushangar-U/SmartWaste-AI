import os
import sys
import unittest
from types import ModuleType
from unittest.mock import patch


os.environ.setdefault("JWT_SECRET", "integration-test-secret")
os.environ.setdefault("USE_MOCK_AGENTS", "true")

from agents.waste_analyzer.schemas import WasteAnalysis
from backend.schemas import AnalysisResult, DecisionResult, RetrievalResult
from backend.services import agent_client
from backend.services.orchestrator import AgentError, process_complaint


def make_analysis(severity: str = "medium") -> AnalysisResult:
    return AnalysisResult(
        waste_types=["plastic"],
        location="residential street",
        duration_days=2,
        severity=severity,
        issue_type="uncollected waste",
        summary="Plastic waste has not been collected for two days.",
    )


def make_retrieval(with_evidence: bool = True) -> RetrievalResult:
    evidence = []
    sources = []
    if with_evidence:
        evidence = [
            {
                "chunk_id": "guide_p3_c01",
                "source": "guide.pdf",
                "page": 3,
                "text": "Routine plastic waste should be collected promptly.",
                "score": 0.81,
            }
        ]
        sources = [{"source": "guide.pdf", "page": 3}]

    return RetrievalResult(
        query="plastic uncollected waste residential street for 2 days",
        answer=(
            "Retrieved guidance supports prompt routine collection."
            if with_evidence
            else "No sufficiently relevant guidance was found."
        ),
        grounded=with_evidence,
        sources=sources,
        evidence=evidence,
    )


def make_decision(
    priority: str = "medium",
    review: bool = False,
    confidence: float = 0.8,
) -> DecisionResult:
    return DecisionResult(
        priority=priority,
        recommended_action="Schedule routine collection.",
        explanation="The complaint is supported by retrieved guidance.",
        supporting_sources=["guide.pdf"],
        requires_human_review=review,
        confidence=confidence,
        validation={"passed": True, "issues": []},
    )


class PipelineIntegrationTests(unittest.TestCase):
    def run_pipeline(self, analysis, retrieval, decision):
        with (
            patch.object(agent_client, "call_analyst", return_value=analysis),
            patch.object(agent_client, "call_retrieval", return_value=retrieval),
            patch.object(agent_client, "call_decision", return_value=decision),
        ):
            return process_complaint(
                "Plastic waste has not been collected for two days."
            )

    def test_normal_medium_complaint(self):
        result = self.run_pipeline(
            make_analysis(),
            make_retrieval(),
            make_decision(),
        )

        self.assertEqual(result.decision.priority.value, "medium")
        self.assertFalse(result.decision.requires_human_review)
        self.assertTrue(result.validation.passed)
        self.assertEqual(result.retrieval.evidence[0].page, 3)
        self.assertAlmostEqual(result.retrieval.evidence[0].score, 0.81)

    def test_high_severity_complaint_requires_review(self):
        result = self.run_pipeline(
            make_analysis(severity="high"),
            make_retrieval(),
            make_decision(priority="high"),
        )

        self.assertTrue(result.decision.requires_human_review)

    def test_critical_or_low_confidence_decision_requires_review(self):
        result = self.run_pipeline(
            make_analysis(),
            make_retrieval(),
            make_decision(priority="critical", confidence=0.4),
        )

        self.assertEqual(result.decision.priority.value, "critical")
        self.assertTrue(result.decision.requires_human_review)
        self.assertFalse(result.validation.passed)
        self.assertTrue(
            any("Low-confidence" in item for item in result.validation.warnings)
        )

    def test_missing_rag_evidence_requires_review(self):
        decision = make_decision()
        decision.supporting_sources = []
        result = self.run_pipeline(
            make_analysis(),
            make_retrieval(with_evidence=False),
            decision,
        )

        self.assertFalse(result.retrieval.grounded)
        self.assertTrue(result.decision.requires_human_review)
        self.assertFalse(result.validation.passed)
        self.assertTrue(
            any("No supporting evidence" in item for item in result.validation.warnings)
        )

    def test_weak_rag_answer_requires_review_even_with_chunks(self):
        retrieval = make_retrieval()
        retrieval.grounded = False
        result = self.run_pipeline(
            make_analysis(),
            retrieval,
            make_decision(),
        )

        self.assertTrue(result.retrieval.evidence)
        self.assertTrue(result.decision.requires_human_review)
        self.assertTrue(
            any("sufficiently grounded" in item for item in result.validation.warnings)
        )

    def test_agent_api_failure_is_wrapped(self):
        with patch.object(
            agent_client,
            "call_analyst",
            side_effect=RuntimeError("external service unavailable"),
        ):
            with self.assertRaises(AgentError) as error:
                process_complaint(
                    "Plastic waste has not been collected for two days."
                )

        self.assertEqual(error.exception.stage, "analyst")

    def test_adapters_preserve_metadata_and_normalize_decision(self):
        analyzer_module = ModuleType("agents.waste_analyzer.agent")
        analyzer_module.analyze_complaint = lambda text: WasteAnalysis(
            waste_types=["plastic"],
            location="near a school",
            duration_days=5,
            severity="high",
            issue_type="illegal dumping",
            summary=text,
        )

        captured = {}
        knowledge_module = ModuleType("agents.knowledge_agent.rag_agent")

        def fake_generate(analysis):
            captured["knowledge_input"] = analysis
            return {
                "query": "plastic dumping near a school for 5 days",
                "answer": "Grounded school-area collection guidance.",
                "grounded": True,
                "sources": [{"source": "policy.pdf", "page": 9}],
                "evidence": [
                    {
                        "chunk_id": "policy_p9_c02",
                        "source": "policy.pdf",
                        "page": 9,
                        "text": "Waste near schools should receive prompt attention.",
                        "score": 0.88,
                    }
                ],
            }

        knowledge_module.generate_answer = fake_generate
        decision_module = ModuleType("agents.decision.agent")

        def fake_decide(analysis, evidence, grounded_knowledge=None):
            captured["decision_evidence"] = evidence
            captured["grounded_knowledge"] = grounded_knowledge
            return {
                "priority": "CRITICAL",
                "recommended_action": "Send an authorized team to inspect the site.",
                "explanation": "School proximity and duration require escalation.",
                "supporting_sources": ["policy.pdf"],
                "requires_human_review": True,
                "confidence": 0.9,
                "validation": {"passed": True, "issues": []},
            }

        decision_module.decide = fake_decide

        with (
            patch.object(agent_client.settings, "use_mock_agents", False),
            patch.dict(
                sys.modules,
                {
                    "agents.waste_analyzer.agent": analyzer_module,
                    "agents.knowledge_agent.rag_agent": knowledge_module,
                    "agents.decision.agent": decision_module,
                },
            ),
        ):
            analysis = agent_client.call_analyst(
                "Plastic has been dumped near a school for five days."
            )
            retrieval = agent_client.call_retrieval(analysis)
            decision = agent_client.call_decision(analysis, retrieval)

        self.assertIsInstance(captured["knowledge_input"], WasteAnalysis)
        self.assertTrue(retrieval.evidence[0].text.startswith("Waste near schools"))
        self.assertEqual(retrieval.evidence[0].page, 9)
        self.assertAlmostEqual(retrieval.evidence[0].score, 0.88)
        self.assertEqual(
            captured["decision_evidence"][0]["snippet"],
            retrieval.evidence[0].text,
        )
        self.assertEqual(captured["decision_evidence"][0]["page"], 9)
        self.assertEqual(captured["grounded_knowledge"], retrieval.answer)
        self.assertEqual(decision.priority.value, "critical")
        self.assertTrue(decision.requires_human_review)


if __name__ == "__main__":
    unittest.main()
