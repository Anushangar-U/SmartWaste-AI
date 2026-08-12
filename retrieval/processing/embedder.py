from __future__ import annotations

from typing import TYPE_CHECKING, Sequence, TypedDict

from sentence_transformers import SentenceTransformer

if TYPE_CHECKING:
    from retrieval.processing.chunker import ChunkRecord


DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_BATCH_SIZE = 32


class EmbeddingRecord(TypedDict):
    """A chunk and its embedding, kept together for later indexing."""

    chunk_id: str
    source: str
    page: int
    text: str
    embedding: list[float]


def embed_chunks(
    chunks: Sequence[ChunkRecord],
    model_name: str = DEFAULT_MODEL_NAME,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> list[EmbeddingRecord]:
    """Generate one embedding vector for every supplied chunk.

    The returned records retain the original chunk metadata so a future vector
    index can trace a matching vector back to its PDF source and page.
    """

    if batch_size <= 0:
        raise ValueError("batch_size must be greater than 0")
    if not chunks:
        return []

    model = SentenceTransformer(model_name)
    texts = [chunk["text"] for chunk in chunks]
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
    )

    embedding_records: list[EmbeddingRecord] = []
    for chunk, vector in zip(chunks, vectors, strict=True):
        embedding_records.append(
            {
                "chunk_id": chunk["chunk_id"],
                "source": chunk["source"],
                "page": chunk["page"],
                "text": chunk["text"],
                "embedding": [float(value) for value in vector],
            }
        )

    return embedding_records


def main() -> None:
    """Run ingestion, chunking, and embedding as a command-line check."""

    from retrieval.ingest import load_all_pdfs
    from retrieval.processing.chunker import chunk_page_records

    page_records = load_all_pdfs()
    chunks = chunk_page_records(page_records)
    embedded_chunks = embed_chunks(chunks)

    if len(embedded_chunks) != len(chunks):
        raise RuntimeError("Embedding count does not match chunk count.")

    embedding_dimension = len(embedded_chunks[0]["embedding"]) if embedded_chunks else 0

    print(f"Chunks embedded: {len(embedded_chunks)}")
    print(f"Embedding dimension: {embedding_dimension}")
    print(f"Model name: {DEFAULT_MODEL_NAME}")
    print("Embedding count matches chunk count: yes")


if __name__ == "__main__":
    main()
