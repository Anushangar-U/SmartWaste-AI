from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from retrieval.ingest import PageRecord


DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_MIN_CHUNK_LENGTH = 50


class ChunkRecord(TypedDict):
    """Text chunk with enough metadata to trace it back to the source PDF page."""

    chunk_id: str
    source: str
    page: int
    text: str


def make_source_slug(source: str) -> str:
    """Convert a PDF filename into a readable identifier for chunk IDs."""

    source_stem = Path(source).stem.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", source_stem).strip("_")
    return slug or "document"


def split_text_into_chunks(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """Split text into overlapping chunks while keeping the original wording."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must not be negative")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    text = text.strip()
    if not text:
        return []

    chunks: list[str] = []
    text_length = len(text)
    start = 0

    while start < text_length:
        end = min(start + chunk_size, text_length)

        if end < text_length:
            minimum_break = start + chunk_overlap + 1
            newline_break = text.rfind("\n", minimum_break, end)
            space_break = text.rfind(" ", minimum_break, end)
            break_position = max(newline_break, space_break)

            if break_position > start:
                end = break_position

        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(chunk_text)

        if end >= text_length:
            break

        next_start = end - chunk_overlap
        if next_start <= start:
            next_start = end
        start = next_start

    return chunks


def chunk_page_records(
    page_records: list[PageRecord],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    min_chunk_length: int = DEFAULT_MIN_CHUNK_LENGTH,
) -> list[ChunkRecord]:
    """Convert page-level records into chunk-level records."""

    if min_chunk_length < 0:
        raise ValueError("min_chunk_length must not be negative")

    chunk_records: list[ChunkRecord] = []

    for page_record in page_records:
        source = page_record["source"]
        page = page_record["page"]
        source_slug = make_source_slug(source)
        page_chunks = split_text_into_chunks(
            page_record["text"],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        for chunk_number, chunk_text in enumerate(page_chunks, start=1):
            if len(chunk_text.strip()) < min_chunk_length:
                continue

            chunk_records.append(
                {
                    "chunk_id": f"{source_slug}_p{page}_c{chunk_number:02d}",
                    "source": source,
                    "page": page,
                    "text": chunk_text,
                }
            )

    return chunk_records


def print_chunking_summary(
    page_records: list[PageRecord],
    chunk_records: list[ChunkRecord],
) -> None:
    """Print a short summary for command-line checks."""

    chunk_lengths = [len(chunk["text"]) for chunk in chunk_records]
    chunks_per_source = Counter(chunk["source"] for chunk in chunk_records)

    print(f"Page records: {len(page_records)}")
    print(f"Chunks created: {len(chunk_records)}")
    print("Chunks per source:")

    if chunks_per_source:
        for source, count in sorted(chunks_per_source.items()):
            print(f"  {source}: {count}")
    else:
        print("  None")

    if chunk_lengths:
        average_length = sum(chunk_lengths) / len(chunk_lengths)
        print(f"Minimum chunk length: {min(chunk_lengths)}")
        print(f"Maximum chunk length: {max(chunk_lengths)}")
        print(f"Average chunk length: {average_length:.1f}")
    else:
        print("Minimum chunk length: 0")
        print("Maximum chunk length: 0")
        print("Average chunk length: 0.0")


def main() -> None:
    """Load PDFs through ingestion, then chunk the resulting page records."""

    from retrieval.ingest import load_all_pdfs

    page_records = load_all_pdfs()
    chunk_records = chunk_page_records(page_records)
    print_chunking_summary(page_records, chunk_records)


if __name__ == "__main__":
    main()
