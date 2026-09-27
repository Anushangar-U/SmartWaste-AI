import unittest
from evaluation.metrics import evaluate


class EvaluationTests(unittest.TestCase):
    def test_unreviewed_never_counts_and_empty_metrics_are_null(self):
        report = evaluate([{"id":"a","review_status":"UNREVIEWED","reference":{"agent1":{"severity":"high"}}}],
                          {"a":{"analysis":{"severity":"high"}}})
        self.assertEqual(report["evaluated_records"], 0)
        self.assertIsNone(report["metrics"]["severity_agreement"]["value"])

    def test_known_rankings_and_partial_labels(self):
        record = {"id":"a","review_status":"REVIEWED","reference":{"retrieval":{
            "relevance":{"one":"irrelevant","two":"relevant","three":"partially_relevant"},"relevant_ids_complete":True}}}
        prediction = {"a":{"retrieval":{"evidence":[{"chunk_id":n,"source":"x"} for n in ["one","two","three"]]}}}
        metrics = evaluate([record], prediction)["metrics"]
        self.assertEqual(metrics["mrr_at_5"]["value"], 0.5)
        self.assertEqual(metrics["precision_at_3"]["value"], 1/3)
        self.assertEqual(metrics["graded_precision_at_3"]["value"], 0.5)
        self.assertEqual(metrics["recall_at_5"]["value"], 1)

    def test_claim_labels_must_match_output(self):
        record = {"id":"a","review_status":"REVIEWED","reference":{"system":{"output_sha256":"old","claims":["supported"]}}}
        self.assertIsNone(evaluate([record], {"a":{"output_sha256":"new"}})["metrics"]["supported_claim_rate"]["value"])
        self.assertEqual(evaluate([record], {"a":{"output_sha256":"old"}})["metrics"]["supported_claim_rate"]["value"], 1)
