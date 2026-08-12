from __future__ import annotations

import argparse
from functools import lru_cache
from pathlib import Path
from typing import TypedDict

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from retrieval.processing.embedder import DEFAULT_MODEL_NAME
from retrieval.vector_store.faiss_store import (
    DEFAULT_INDEX_FILENAME,
    DEFAULT_METADATA_FILENAME,
    DEFAULT_VECTOR_STORE_DIR,
    ChunkMetadata,
    load_index,
)


DEFAULT_TOP_K = 5


class RetrievalResult(TypedDict):
    chunk_id: str
    source: str
    page: int
    text: str
    score: float


@lru_cache(maxsize=1)
def _load_model(model_name: str = DEFAULT_MODEL_NAME) -> SentenceTransformer:
    return SentenceTransformer(model_name)


@lru_cache(maxsize=1)
def _load_vector_store(
    store_dir: Path = DEFAULT_VECTOR_STORE_DIR,
    index_filename: str = DEFAULT_INDEX_FILENAME,
    metadata_filename: str = DEFAULT_METADATA_FILENAME,
) -> tuple[faiss.Index, list[ChunkMetadata]]:
    loaded_store = load_index(store_dir, index_filename, metadata_filename)
    return loaded_store["index"], loaded_store["metadata"]


def embed_query(query: str, model_name: str = DEFAULT_MODEL_NAME) -> np.ndarray:
    """Create a normalized query embedding for cosine-similarity search."""

    cleaned_query = query.strip()
    if not cleaned_query:
        raise ValueError("Query cannot be empty.")

    model = _load_model(model_name)
    query_vector = np.array(
        model.encode([cleaned_query], convert_to_numpy=True),
        dtype="float32",
    )
    faiss.normalize_L2(query_vector)

    return query_vector


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    model_name: str = DEFAULT_MODEL_NAME,
) -> list[RetrievalResult]:
    """Return the top-k semantic matches from the saved FAISS index."""

    if top_k <= 0:
        raise ValueError("top_k must be greater than 0.")

    index, metadata = _load_vector_store()
    if index.ntotal == 0:
        return []
    if len(metadata) != index.ntotal:
        raise RuntimeError("Metadata count does not match FAISS vector count.")

    query_vector = embed_query(query, model_name)
    if query_vector.shape[1] != index.d:
        raise RuntimeError(
            f"Query embedding dimension {query_vector.shape[1]} does not match "
            f"FAISS index dimension {index.d}."
        )

    safe_top_k = min(top_k, index.ntotal)
    scores, indices = index.search(query_vector, safe_top_k)

    results: list[RetrievalResult] = []
    for score, index_position in zip(scores[0], indices[0], strict=True):
        if index_position < 0:
            continue

        chunk_metadata = metadata[int(index_position)]
        results.append(
            {
                "chunk_id": chunk_metadata["chunk_id"],
                "source": chunk_metadata["source"],
                "page": chunk_metadata["page"],
                "text": chunk_metadata["text"],
                "score": float(score),
            }
        )

    return results


def _print_results(query: str, results: list[RetrievalResult]) -> None:
    print("Query:")
    print(query)
    print()

    if not results:
        print("No results found.")
        return

    for result_number, result in enumerate(results, start=1):
        print(f"Result {result_number}")
        print(f"Chunk ID: {result['chunk_id']}")
        print(f"Source: {result['source']}")
        print(f"Page: {result['page']}")
        print(f"Similarity: {result['score']:.4f}")
        print("Text:")
        print(result["text"])
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Search the SmartWaste-AI FAISS index.")
    parser.add_argument("query", nargs="*", help="Natural-language search query.")
    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help=f"Number of results to return. Default: {DEFAULT_TOP_K}",
    )
    args = parser.parse_args()

    query = " ".join(args.query).strip()
    if not query:
        query = input("Enter your question: ").strip()

    try:
        results = retrieve(query, top_k=args.top_k)
    except ValueError as error:
        raise SystemExit(f"Error: {error}") from error

    _print_results(query, results)


if __name__ == "__main__":
    main()
