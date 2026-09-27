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
