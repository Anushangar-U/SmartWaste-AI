"""Audit-only output helpers. Never persist credentials or bearer tokens."""
from pathlib import Path
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / "audit" / "member4"
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
BASELINE = "2a8615c2b24b5c75ab024de8af4525e2f428f165"

from dotenv import dotenv_values

_private_values = [
    value for name, value in {**dotenv_values(ROOT / ".env"), **os.environ}.items()
    if re.search(r"KEY|SECRET|PASSWORD|TOKEN", name, re.I)
    and isinstance(value, str) and len(value) >= 6
]


def sanitize(value):
    if isinstance(value, dict):
        return {
            str(key): ("[REDACTED]" if str(key).lower() in {
                "access_token", "token", "password", "password_hash",
                "authorization", "api_key", "jwt_secret", "refresh_token",
            } else sanitize(item))
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        for private_value in _private_values:
            value = value.replace(private_value, "[REDACTED]")
        value = re.sub(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", "[REDACTED_JWT]", value)
        return value
    return value


def save_json(name, data):
    target = AUDIT / "evidence" / "json" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(sanitize(data), ensure_ascii=False, indent=2), encoding="utf-8")


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def error_record(exc):
    # Exception strings can include provider headers or request data; omit them.
    result = {"type": type(exc).__name__}
    code = getattr(exc, "status_code", None)
    if code is not None:
        result["http_status"] = code
    return result
