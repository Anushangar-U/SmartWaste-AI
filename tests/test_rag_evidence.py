import unittest
from types import SimpleNamespace
from unittest.mock import patch

from agents.knowledge_agent import rag_agent
from agents.waste_analyzer.schemas import WasteAnalysis


ANALYSIS = WasteAnalysis(
    waste_types=["organic"],
    location="residential street",
    duration_days=2,
    severity="medium",
    issue_type="uncollected waste",
    summary="Household waste has not been collected for two days.",
)


def chunk(source, page, score):
    return {
        "chunk_id": f"{source}_{page}",
        "source": source,
        "page": page,
        "text": f"Guidance from {source} page {page}.",
        "score": score,
    }


class EvidenceFilteringTests(unittest.TestCase):
    def generate(self, chunks, content="Use guidance [1]."):
        retrieval = {
            "query": "household waste",
            "evidence": chunks,
            "sources": [
                {"source": item["source"], "page": item["page"]}
                for item in chunks
            ],
        }
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=lambda **kwargs: response)
            )
        )
        with (
            patch.object(rag_agent, "retrieve_for_analysis", return_value=retrieval) as get_evidence,
            patch.object(rag_agent, "_get_client", return_value=client) as get_client,
            patch.object(client.chat.completions, "create", wraps=client.chat.completions.create) as create,
        ):
            result = rag_agent.generate_answer(ANALYSIS)
        get_evidence.assert_called_once_with(ANALYSIS, top_k=5)
        return result, get_client.call_count, create.call_args

    def test_all_chunks_above_threshold(self):
        chunks = [chunk("one.pdf", 2, 0.8), chunk("two.pdf", 7, 0.5)]
        result, calls, prompt_call = self.generate(chunks)
        self.assertTrue(result["grounded"])
        self.assertEqual(result["evidence"], chunks)
        self.assertEqual(result["sources"], [
            {"source": "one.pdf", "page": 2},
            {"source": "two.pdf", "page": 7},
        ])
        self.assertEqual(calls, 1)
        self.assertIn("two.pdf", prompt_call.kwargs["messages"][1]["content"])

    def test_mixed_scores_exclude_weak_chunk_from_prompt_and_result(self):
        strong = chunk("strong.pdf", 9, 0.72)
        weak = chunk("weak.pdf", 3, 0.34)
        result, _, prompt_call = self.generate([strong, weak])
        self.assertEqual(result["evidence"], [strong])
        self.assertEqual(result["sources"], [{"source": "strong.pdf", "page": 9}])
        prompt = prompt_call.kwargs["messages"][1]["content"]
        self.assertIn("strong.pdf", prompt)
        self.assertNotIn("weak.pdf", prompt)

    def test_no_chunks_above_threshold(self):
        result, calls, prompt_call = self.generate([chunk("weak.pdf", 3, 0.34)])
        self.assertFalse(result["grounded"])
        self.assertEqual(result["answer"], rag_agent.INSUFFICIENT_EVIDENCE_MESSAGE)
        self.assertEqual(result["evidence"], [])
        self.assertEqual(result["sources"], [])
        self.assertEqual(calls, 0)
        self.assertIsNone(prompt_call)

    def test_structured_message_content_is_normalized(self):
        result, _, _ = self.generate(
            [chunk("one.pdf", 2, 0.8)],
            content=[{"type": "text", "text": "Use guidance [1]."}],
        )
        self.assertTrue(result["grounded"])
        self.assertEqual(result["answer"], "Use guidance [citation removed].")

    def test_exact_threshold_is_included(self):
        exact = chunk("boundary.pdf", 11, 0.35)
        result, _, prompt_call = self.generate([exact])
        self.assertTrue(result["grounded"])
        self.assertEqual(result["evidence"], [exact])
        self.assertEqual(result["sources"], [{"source": "boundary.pdf", "page": 11}])
        self.assertIn("boundary.pdf", prompt_call.kwargs["messages"][1]["content"])


if __name__ == "__main__":
    unittest.main()
