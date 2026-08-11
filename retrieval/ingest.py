"""Read PDF documents and return cleaned, page-level text records.

This module deliberately covers only the ingestion stage of the RAG pipeline.
It does not split text into chunks or create embeddings.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import TypedDict

import pymupdf


DEFAULT_DOCUMENTS_DIR = Path(__file__).parent / "documents"


class PageRecord(TypedDict):
    """Text extracted from one PDF page."""

    source: str
    page: int
    text: str


def clean_text(text: str) -> str:
    """Make PDF-extracted text readable without changing its meaning.

    Spaces within each line are normalized and runs of blank lines are reduced
    to one blank line. Other text, including headings and terminology, is kept.
    """

    cleaned_lines: list[str] = []
    previous_line_was_blank = False

    for raw_line in text.splitlines():
        line = re.sub(r"[ \t\f\v]+", " ", raw_line).strip()

        if line:
            cleaned_lines.append(line)
            previous_line_was_blank = False
        elif cleaned_lines and not previous_line_was_blank:
            cleaned_lines.append("")
            previous_line_was_blank = True

    return "\n".join(cleaned_lines).strip()


def find_pdf_files(documents_dir: Path | str = DEFAULT_DOCUMENTS_DIR) -> list[Path]:
    """Return the PDF files in a documents directory in a stable order."""

    directory = Path(documents_dir)
    if not directory.is_dir():
        raise FileNotFoundError(f"Documents directory not found: {directory}")

    return sorted(
        (path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".pdf"),
        key=lambda path: path.name.lower(),
    )


def load_all_pdfs(documents_dir: Path | str = DEFAULT_DOCUMENTS_DIR) -> list[PageRecord]:
    """Load every extractable PDF page from *documents_dir*.

    Unreadable PDFs and PDFs without extractable text are reported to stderr and
    skipped, allowing the remaining documents to be ingested.
    """

    page_records: list[PageRecord] = []

    for pdf_path in find_pdf_files(documents_dir):
        records_before_pdf = len(page_records)

        try:
            with pymupdf.open(pdf_path) as pdf_document:
                for page_number, pdf_page in enumerate(pdf_document, start=1):
                    page_text = clean_text(pdf_page.get_text("text"))
                    if not page_text:
                        continue

                    page_records.append(
                        {
                            "source": pdf_path.name,
                            "page": page_number,
                            "text": page_text,
                        }
                    )
        except Exception as error:
            del page_records[records_before_pdf:]
            print(f"Warning: could not read '{pdf_path.name}': {error}", file=sys.stderr)
            continue

        if len(page_records) == records_before_pdf:
            print(
                f"Warning: '{pdf_path.name}' contains no extractable text.",
                file=sys.stderr,
            )

    return page_records


def main() -> None:
    """Run ingestion and print a short, human-readable summary."""

    try:
        pdf_files = find_pdf_files()
        page_records = load_all_pdfs()
    except FileNotFoundError as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1) from error

    source_names = [pdf_path.name for pdf_path in pdf_files]
    total_characters = sum(len(record["text"]) for record in page_records)

    print(f"PDFs processed: {len(pdf_files)}")
    print(f"Pages extracted: {len(page_records)}")
    print(f"Source filenames: {', '.join(source_names) if source_names else 'None'}")
    print(f"Total characters extracted: {total_characters}")


if __name__ == "__main__":
    main()
