"""Check audit evidence, credentials and production integrity without changing production."""
import json
import re
import subprocess
from collections import Counter

from common import AUDIT, ROOT, BASELINE, _private_values, digest, now, save_json


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main():
    environment = json.loads((AUDIT / "evidence/json/environment.json").read_text(encoding="utf-8"))
    failures = []
    modified = []
    for group in ["production_hashes_before", "vector_store_hashes_before"]:
        for name, expected in environment[group].items():
            path = ROOT / name
            if not path.is_file() or digest(path) != expected:
                modified.append(name)
    if modified:
        failures.append("Production or vector-store hash mismatch")
    changed = git("diff", "--name-only", BASELINE).splitlines()
    staged = git("diff", "--cached", "--name-only").splitlines()
    untracked = git("ls-files", "--others", "--exclude-standard").splitlines()
    outside_scope = sorted({p for p in changed + staged + untracked if not p.startswith("audit/member4/")})
    if outside_scope:
        failures.append("Changes outside audit/member4")
    if git("rev-parse", "origin/main") != BASELINE:
        failures.append("Local origin/main reference differs from audited baseline")
    if git("branch", "--show-current") != "audit/member4-ir-security":
        failures.append("Unexpected current branch")
    cases = (AUDIT / "test_cases.md").read_text(encoding="utf-8")
    fields = ["Test ID", "Test Objective", "Input / Attack Scenario", "Expected Behaviour", "Actual Behaviour", "Evidence", "Observations", "Conclusion"]
    blocks = re.split(r"(?m)^Test ID: ", cases)[1:]
    outcomes = {}
    for block in blocks:
        block = "Test ID: " + block
        labels = re.findall(r"(?m)^(" + "|".join(re.escape(f) for f in fields) + r"): ", block)
        test_id = block.splitlines()[0].split(": ")[1]
        if labels != fields:
            failures.append("Invalid assignment fields: " + test_id)
        match = re.search(r"(?m)^Conclusion: (PASS|PARTIAL|FAIL)$", block)
        outcomes[test_id] = match.group(1) if match else "INVALID"
    if set(outcomes) != {f"IR-{i:02d}" for i in range(1, 25)}:
        failures.append("Test case IDs missing or unexpected")
    counts = dict(Counter(outcomes.values()))
    if counts != {"PASS": 11, "PARTIAL": 11, "FAIL": 2}:
        failures.append("Outcome counts differ from documented results")
    secret_files, missing_evidence, manifest = [], [], {}
    final_file = AUDIT / "evidence/json/final-integrity.json"
    for path in sorted(AUDIT.rglob("*")):
        if not path.is_file() or path == final_file:
            continue
        relative = path.relative_to(AUDIT).as_posix()
        manifest[relative] = digest(path)
        if path.name == ".env" or "__pycache__" in path.parts:
            failures.append("Unexpected artifact: " + relative)
        if path.suffix.lower() in {".md", ".txt", ".json", ".py"}:
            content = path.read_text(encoding="utf-8")
            if any(value in content for value in _private_values) or re.search(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", content):
                secret_files.append(relative)
            if path.suffix == ".json":
                json.loads(content)
    for ref in re.findall(r"evidence/(?:json|logs)/[A-Za-z0-9_.-]+\.(?:json|png|txt)", cases):
        if not (AUDIT / ref).is_file():
            missing_evidence.append(ref)
    if secret_files:
        failures.append("Sensitive value detected; file paths only recorded")
    if missing_evidence:
        failures.append("Test-case evidence references are missing")
    result = {
        "checked_at": now(), "audited_commit": BASELINE,
        "execution_head": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "production_unchanged": not modified,
        "production_files_checked": len(environment["production_hashes_before"]),
        "vector_store_files_checked": len(environment["vector_store_hashes_before"]),
        "hash_mismatch_paths": modified, "outside_scope_paths": outside_scope,
        "secret_scan_passed": not secret_files, "secret_scan_flagged_paths": secret_files,
        "secret_scan_scope": "Known configured credential values and JWT-shaped strings in all audit text; generated PDF renders were separately visually inspected",
        "missing_evidence": missing_evidence, "test_outcomes": outcomes,
        "outcome_counts": counts,
        "execution_coverage": {"dynamic_at_least_partly": 22, "static_only": ["IR-23"], "not_executed_environment": ["IR-09"]},
        "artifact_sha256_excluding_this_file": manifest,
        "failures": failures, "passed": not failures,
    }
    save_json("final-integrity.json", result)
    print(json.dumps({key: result[key] for key in ["production_unchanged", "production_files_checked", "vector_store_files_checked", "secret_scan_passed", "outcome_counts", "failures", "passed"]}, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
