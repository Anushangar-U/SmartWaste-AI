from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Sequence, TypedDict

import faiss
import numpy as np

if TYPE_CHECKING:
    from retrieval.processing.embedder import EmbeddingRecord


DEFAULT_VECTOR_STORE_DIR = Path(__file__).parent / "data"
DEFAULT_INDEX_FILENAME = "smartwaste.faiss"
DEFAULT_METADATA_FILENAME = "metadata.json"
DEFAULT_BUILD_INFO_FILENAME = "build_info.json"
EXPECTED_EMBEDDING_DIMENSION = 384


class ChunkMetadata(TypedDict):
    """Metadata that connects a FAISS vector back to its original chunk."""

    chunk_id: str
    source: str
    page: int
    text: str


class LoadedVectorStore(TypedDict):
    """A loaded FAISS index together with its chunk metadata."""

    index: faiss.Index
    metadata: list[ChunkMetadata]


def _embedding_matrix(embedding_records: Sequence[EmbeddingRecord]) -> np.ndarray:
    """Convert embedding records into a float32 matrix for FAISS."""

    if not embedding_records:
        raise ValueError("Cannot build a FAISS index from an empty embedding list.")

    vectors = np.array(
        [record["embedding"] for record in embedding_records],
        dtype="float32",
    )

    if vectors.ndim != 2:
        raise ValueError("Embeddings must form a 2D matrix.")

    return vectors


def _metadata_records(
    embedding_records: Sequence[EmbeddingRecord],
) -> list[ChunkMetadata]:
    """Keep only the fields needed to trace vectors back to chunks."""

    return [
        {
            "chunk_id": record["chunk_id"],
            "source": record["source"],
            "page": record["page"],
            "text": record["text"],
        }
        for record in embedding_records
    ]


def build_index(
    embedding_records: Sequence[EmbeddingRecord],
) -> tuple[faiss.IndexFlatIP, list[ChunkMetadata]]:
    """Build a cosine-similarity FAISS index from embedding records.

    FAISS IndexFlatIP searches by inner product. After L2-normalizing each
    vector, inner product gives cosine similarity.
    """

    vectors = _embedding_matrix(embedding_records)
    faiss.normalize_L2(vectors)

    dimension = vectors.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(vectors)

    return index, _metadata_records(embedding_records)


def save_index(
    index: faiss.Index,
    metadata: Sequence[ChunkMetadata],
    store_dir: Path = DEFAULT_VECTOR_STORE_DIR,
    index_filename: str = DEFAULT_INDEX_FILENAME,
    metadata_filename: str = DEFAULT_METADATA_FILENAME,
    build_info: dict | None = None,
) -> None:
    """Save a FAISS index and its metadata to local generated files."""

    store_dir.mkdir(parents=True, exist_ok=True)

    index_path = store_dir / index_filename
    metadata_path = store_dir / metadata_filename

    faiss.write_index(index, str(index_path))
    metadata_path.write_text(
        json.dumps(list(metadata), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    if build_info is not None:
        (store_dir / DEFAULT_BUILD_INFO_FILENAME).write_text(
            json.dumps(build_info, indent=2), encoding="utf-8"
        )


def validate_index(
    index: faiss.Index,
    metadata: Sequence[ChunkMetadata],
    expected_vector_count: int,
    expected_embedding_dimension: int = EXPECTED_EMBEDDING_DIMENSION,
) -> None:
    """Check a built or reloaded index against the current corpus and model."""
    if index.ntotal != expected_vector_count:
        raise RuntimeError("Indexed vector count does not match processed chunks.")
    if len(metadata) != index.ntotal:
        raise RuntimeError("Metadata count does not match indexed vector count.")
    if index.d != expected_embedding_dimension:
        raise RuntimeError(
            f"Expected embedding dimension {expected_embedding_dimension}, got {index.d}."
        )


def load_index(
    store_dir: Path = DEFAULT_VECTOR_STORE_DIR,
    index_filename: str = DEFAULT_INDEX_FILENAME,
    metadata_filename: str = DEFAULT_METADATA_FILENAME,
) -> LoadedVectorStore:
    """Load a saved FAISS index and its matching metadata."""

    index_path = store_dir / index_filename
    metadata_path = store_dir / metadata_filename

    if not index_path.exists():
        raise FileNotFoundError(f"FAISS index file not found: {index_path}")
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

    index = faiss.read_index(str(index_path))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    return {"index": index, "metadata": metadata}


def main() -> None:
    """Run the full Phase 5 pipeline as a command-line validation."""

    from retrieval.ingest import load_all_pdfs
    from retrieval.processing.chunker import (
        DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE, chunk_page_records,
    )
    from retrieval.processing.embedder import DEFAULT_MODEL_NAME, embed_chunks

    page_records = load_all_pdfs()
    chunks = chunk_page_records(page_records)
    embedding_records = embed_chunks(chunks)

    index, metadata = build_index(embedding_records)
    validate_index(index, metadata, expected_vector_count=len(chunks))
    build_info = {
        "embedding_model": DEFAULT_MODEL_NAME,
        "embedding_dimension": index.d,
        "chunk_size": DEFAULT_CHUNK_SIZE,
        "chunk_overlap": DEFAULT_CHUNK_OVERLAP,
        "vector_count": index.ntotal,
    }
    save_index(index, metadata, build_info=build_info)
    loaded_store = load_index()

    loaded_index = loaded_store["index"]
    loaded_metadata = loaded_store["metadata"]
    validate_index(loaded_index, loaded_metadata, expected_vector_count=len(chunks))

    print(f"Page records: {len(page_records)}")
    print(f"Chunks embedded: {len(embedding_records)}")
    print(f"Indexed vectors: {loaded_index.ntotal}")
    print(f"Embedding dimension: {loaded_index.d}")
    print(f"Model name: {DEFAULT_MODEL_NAME}")
    print(f"Index type: {type(loaded_index).__name__}")
    print(f"Vector store directory: {DEFAULT_VECTOR_STORE_DIR}")
    print("Index reload check: passed")


if __name__ == "__main__":
    main()
