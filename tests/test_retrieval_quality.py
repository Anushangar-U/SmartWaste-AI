import unittest
from agents.knowledge_agent.rag_agent import build_retrieval_query
from agents.waste_analyzer.schemas import WasteAnalysis
from retrieval.processing.quality import select_guidance_pages, deduplicate, rerank
from retrieval.sources import approved_filenames, display_metadata, verify_manifest


class RetrievalQualityTests(unittest.TestCase):
    def test_query_preserves_context_without_repeating_location(self):
        query = build_retrieval_query(WasteAnalysis(waste_types=["mixed"], location="beside a school near the river",
            duration_days=3, severity="high", issue_type="dumping", summary="Mixed waste dumping beside a school near the river for three days."))
        self.assertEqual(query.lower().count("school"), 1)
        self.assertNotIn("near beside", query)
        self.assertEqual(query.lower().count("days"), 1)

    def test_conservative_exclusion_preserves_guidance(self):
        texts = ["Contents\nIndex\nCollection .... 2\nSafety .... 3\nWaste .... 4\nPolicy .... 5",
                 "References\nExample 2020\nAnother 2021\nThird 2022",
                 "References to policy\nStaff must consult guidance before making a decision."]
        included, report = select_guidance_pages([{"source": "test", "page": i+1, "text": t} for i,t in enumerate(texts)])
        self.assertEqual([p["page"] for p in included], [3])
        self.assertEqual(len(report["excluded_pages"]), 2)

    def test_deduplication_and_real_source_identity(self):
        a = {"source": "one", "page": 1, "text": "Guidance on waste collection and management"}
        b = {**a, "page": 2}
        self.assertEqual(deduplicate([a, a, b], 5), [a,b])
        self.assertIn("Action Plan", display_metadata("sri_lanka_waste_policy.pdf")["title"])
        self.assertEqual(verify_manifest(), [])
