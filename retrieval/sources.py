"""Authoritative display metadata; historical filename identifiers remain compatible."""
import hashlib
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def manifest():
    return {s["filename"]: s for s in json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))}


def display_metadata(filename):
    item = manifest().get(filename, {})
    return {key: item[key] for key in ["source_id", "title", "issuer", "year", "jurisdiction", "document_type", "topics", "source_tier", "authority_score"] if key in item}


def verify_manifest():
    failures = []
    for name, record in manifest().items():
        path = ROOT / "documents" / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
            failures.append(name)
    return failures
