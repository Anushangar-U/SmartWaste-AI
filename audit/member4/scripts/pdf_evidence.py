"""Verify actual source pages and render a small sample for visual review."""
import json
from collections import Counter
from common import ROOT, AUDIT, digest, now, save_json
import pymupdf
from retrieval.ingest import clean_text


def normalized(text):
    return " ".join(text.split())


def main():
    passages = {}
    for path in sorted((AUDIT / "evidence/json").glob("IR-*-retrieval.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        for item in record.get("before_filter", []) + record.get("direct_complaint_ranking", []):
            passages[item["chunk_id"]] = item
    verification = []
    for item in passages.values():
        path = ROOT / "retrieval/documents" / item["source"]
        entry = {"chunk_id": item["chunk_id"], "source": item["source"], "page": item["page"], "source_exists": path.is_file()}
        if path.is_file():
            with pymupdf.open(path) as doc:
                entry["pdf_page_count"] = len(doc)
                entry["page_exists"] = 1 <= item["page"] <= len(doc)
                if entry["page_exists"]:
                    text = clean_text(doc[item["page"] - 1].get_text())
                    entry["passage_found_after_whitespace_normalization"] = normalized(item["text"]) in normalized(text)
                    entry["source_page_excerpt"] = text[:1800]
        verification.append(entry)
    docs = []
    for path in sorted((ROOT / "retrieval/documents").glob("*.pdf")):
        with pymupdf.open(path) as doc:
            docs.append({"filename": path.name, "sha256": digest(path), "page_count": len(doc), "first_three_pages_text": [clean_text(doc[i].get_text())[:2200] for i in range(min(3, len(doc)))]})
    save_json("IR-10-pdf-verification.json", {"executed_at": now(), "method": "Actual PyMuPDF text extraction; page is 1-based PDF page, not printed page number.", "unique_passages_checked": len(verification), "passages": verification, "document_identity": docs})
    sample_pages = [
        ("who_un_environment_guidance.pdf", 153),
        ("who_un_environment_guidance.pdf", 53),
        ("sri_lanka_waste_policy.pdf", 45),
        ("sri_lanka_waste_policy.pdf", 1),
        ("sri_lanka_plastic_action_plan.pdf", 1),
    ]
    for source, page in sample_pages:
        with pymupdf.open(ROOT / "retrieval/documents" / source) as doc:
            doc[page - 1].get_pixmap(matrix=pymupdf.Matrix(1, 1)).save(str(AUDIT / "evidence/logs" / f"PDF-{source[:-4]}-p{page}.png"))
    comparisons = {}
    for test_id in ("IR-01", "IR-05", "IR-06", "IR-07"):
        item = json.loads((AUDIT / f"evidence/json/{test_id}-retrieval.json").read_text(encoding="utf-8"))
        comparisons[test_id] = {
            kind: [{"rank": rank, "chunk_id": chunk["chunk_id"], "source": chunk["source"], "page": chunk["page"], "score": chunk["score"]} for rank, chunk in enumerate(item[kind], 1)]
            for kind in ("before_filter", "direct_complaint_ranking")
        }
    for kind in ("before_filter", "direct_complaint_ranking"):
        baseline = {item["chunk_id"] for item in comparisons["IR-01"][kind]}
        for test_id in ("IR-05", "IR-06"):
            ids = {item["chunk_id"] for item in comparisons[test_id][kind]}
            comparisons[test_id][kind + "_overlap_with_IR01"] = len(baseline & ids)
    save_json("ranking-comparison.json", comparisons)
    print("Verified", len(verification), "unique passages; mismatches", sum(not item.get("passage_found_after_whitespace_normalization") for item in verification), flush=True)


if __name__ == "__main__":
    main()
