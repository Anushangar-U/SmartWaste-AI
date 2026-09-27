import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import faiss
import numpy as np

from retrieval.vector_store.faiss_store import (
    DEFAULT_BUILD_INFO_FILENAME,
    save_index,
    validate_index,
)


class FaissBuildValidationTests(unittest.TestCase):
    def test_count_comes_from_current_corpus(self):
        index = SimpleNamespace(ntotal=3, d=384)
        metadata = [{"chunk_id": str(number)} for number in range(3)]
        validate_index(index, metadata, expected_vector_count=3)

    def test_vector_metadata_and_dimension_mismatches_are_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "processed chunks"):
            validate_index(SimpleNamespace(ntotal=2, d=384), [{}, {}], 3)
        with self.assertRaisesRegex(RuntimeError, "Metadata count"):
            validate_index(SimpleNamespace(ntotal=2, d=384), [{}], 2)
        with self.assertRaisesRegex(RuntimeError, "embedding dimension"):
            validate_index(SimpleNamespace(ntotal=2, d=128), [{}, {}], 2)

    def test_build_info_is_saved_without_changing_index_format(self):
        index = faiss.IndexFlatIP(384)
        index.add(np.zeros((2, 384), dtype="float32"))
        metadata = [
            {"chunk_id": str(number), "source": "guide.pdf", "page": number + 1, "text": "Guide"}
            for number in range(2)
        ]
        build_info = {
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "embedding_dimension": 384,
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "vector_count": 2,
        }
        with tempfile.TemporaryDirectory() as directory:
            store_dir = Path(directory)
            save_index(index, metadata, store_dir=store_dir, build_info=build_info)
            self.assertEqual(
                json.loads((store_dir / DEFAULT_BUILD_INFO_FILENAME).read_text(encoding="utf-8")),
                build_info,
            )
            self.assertEqual(faiss.read_index(str(store_dir / "smartwaste.faiss")).ntotal, 2)
            self.assertEqual(
                json.loads((store_dir / "metadata.json").read_text(encoding="utf-8")),
                metadata,
            )


if __name__ == "__main__":
    unittest.main()
