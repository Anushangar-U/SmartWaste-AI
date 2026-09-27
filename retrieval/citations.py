"""Check citation integrity, not semantic entailment or legal correctness."""
import hashlib
import re
from functools import lru_cache
import pymupdf
from retrieval import sources

CITATION = re.compile(r"\[(\d+)\]")


def normalized(text):
    return " ".join(text.split())


@lru_cache(maxsize=128)
def _page_text(path, page, mtime, size, expected_hash):
    from pathlib import Path
    file = Path(path)
    if hashlib.sha256(file.read_bytes()).hexdigest() != expected_hash:
        return None
    with pymupdf.open(file) as pdf:
        if page < 1 or page > len(pdf):
            return None
        return normalized(pdf[page - 1].get_text())


def verify_passage(item):
    record = sources.manifest().get(item["source"])
    if not record:
        return False
    path = sources.ROOT / "documents" / record["filename"]
    try:
        stat = path.stat()
        text = _page_text(str(path), int(item["page"]), stat.st_mtime_ns, stat.st_size, record["sha256"])
        passage = normalized(item["text"])
        return bool(text and passage and passage in text)
    except (OSError, ValueError, TypeError, RuntimeError):
        return False


def sensitive_claim_issues(answer, evidence):
    issues = []
    clean = CITATION.sub("", answer)
    if re.search(r"\b(law|legally|statutory|regulation|mandatory|legal requirement)\b", clean, re.I):
        issues.append("Legal/regulatory wording requires staff verification; lexical checks do not establish legal authority.")
    for sentence in re.split(r"(?<=[.!?])\s+", answer):
        body = CITATION.sub("", sentence)
        quantities = re.findall(r"\b(\d+(?:\.\d+)?)\s*(?:hours?|days?|weeks?|months?|years?|kg|kilograms?|litres?|liters?|percent|%)\b", body, re.I)
        if quantities:
            ids = [int(n) for n in CITATION.findall(sentence)]
            passages = [evidence[i - 1]["text"] for i in ids if 1 <= i <= len(evidence)]
            joined = " ".join(passages)
            if not passages or any(not re.search(r"\b" + re.escape(n) + r"\b", joined) for n in quantities):
                issues.append("An exact quantity/time claim lacks identifiable support in its cited passage; staff verification required.")
    return list(dict.fromkeys(issues))


def inspect_answer(answer, evidence, verifier=None):
    verifier = verifier or verify_passage
    ids = sorted(set(int(n) for n in CITATION.findall(answer)))
    valid, invalid, issues = [], [], []
    if answer.strip() and not ids:
        issues.append("Generated answer has no numbered evidence citations.")
    for number in ids:
        if not 1 <= number <= len(evidence) or not verifier(evidence[number - 1]):
            invalid.append(number)
        else:
            valid.append(number)
    if invalid:
        issues.append("Removed invalid citations or citations whose source/page/passage could not be verified.")
    issues.extend(sensitive_claim_issues(answer, evidence))
    cleaned = CITATION.sub(lambda match: "[citation removed]" if int(match.group(1)) in invalid else match.group(0), answer)
    return cleaned, {"passed": not issues, "valid_citations": valid, "invalid_citations": invalid,
        "issues": issues, "claim_verification": "not_independently_verified"}
