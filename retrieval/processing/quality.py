"""Conservative, inspectable exclusion rules; no automatic legal relevance claims."""
import re
from collections import Counter

# Inspected reference-only page in the hash-verified supplied PDF. Re-review if corpus changes.
REVIEWED_EXCLUSIONS = {("beyond_age_of_waste.pdf", 90): "references_reviewed"}


def exclusion_reason(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "empty"
    heading = " ".join(lines[:6]).lower()
    if re.search(r"\b(table of contents|contents)\b", heading):
        entries = sum(bool(re.search(r"\.{3,}|\s\d+\s*$", line)) for line in lines[2:])
        if len(lines) >= 6 and entries >= (len(lines) - 2) * 0.5:
            return "contents"
    if re.match(r"^(references|bibliography)\b", heading):
        citations = sum(bool(re.search(r"https?://|doi:|\b(?:19|20)\d{2}\b", line)) for line in lines[1:])
        if len(lines) >= 4 and citations >= (len(lines) - 1) * 0.7:
            return "references"
    if len(text) >= 50 and sum(c.isalnum() for c in text) / len(text) < 0.15:
        return "extraction_noise"
    return None


def select_guidance_pages(pages):
    included, excluded = [], []
    for page in pages:
        reason = REVIEWED_EXCLUSIONS.get((page["source"], page["page"])) or exclusion_reason(page["text"])
        if reason:
            excluded.append({"source": page["source"], "page": page["page"], "reason": reason})
        else:
            included.append(page)
    return included, {"excluded_pages": excluded, "excluded_counts": dict(Counter(p["reason"] for p in excluded))}


def deduplicate(results, top_k):
    kept = []
    for item in results:
        words = set(re.findall(r"\w+", item["text"].lower()))
        duplicate = False
        for previous in kept:
            if (item["source"], item["page"]) != (previous["source"], previous["page"]):
                continue
            other = set(re.findall(r"\w+", previous["text"].lower()))
            if words and len(words & other) / len(words | other) >= 0.85:
                duplicate = True
                break
        if not duplicate:
            kept.append(item)
        if len(kept) >= top_k:
            break
    return kept


def rerank(results, query, top_k):
    """Lightweight deterministic reranking using source topics and lexical overlap.

    FAISS similarity remains the primary signal. This adds small, inspectable
    bonuses for query/topic overlap and avoids treating the result as a truth score.
    """
    from retrieval.sources import manifest
    query_words = set(re.findall(r"\w+", query.lower()))
    ranked = []
    for position, item in enumerate(results):
        source = manifest().get(item["source"], {})
        topic_words = set(re.findall(r"\w+", " ".join(source.get("topics", [])).lower()))
        text_words = set(re.findall(r"\w+", item["text"].lower()))
        topic_overlap = len(query_words & topic_words)
        lexical_overlap = len(query_words & text_words)
        # Keep semantic score dominant; bonuses are intentionally small.
        rerank_score = float(item.get("score", 0.0)) + min(topic_overlap, 4) * 0.025 + min(lexical_overlap, 8) * 0.004
        ranked.append((rerank_score, -position, item))
    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [item for _, _, item in ranked[:top_k]]
