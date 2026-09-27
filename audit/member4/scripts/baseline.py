"""Re-run README baseline commands and fingerprint the audited environment."""
import importlib.metadata
import os
import platform
import subprocess
import sys

from common import ROOT, AUDIT, BASELINE, digest, now, sanitize, save_json
from dotenv import dotenv_values


def main():
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", BASELINE, "HEAD"], cwd=ROOT).returncode
    changed = subprocess.check_output(["git", "diff", "--name-only", BASELINE], cwd=ROOT, text=True).splitlines()
    if ancestor or any(not name.startswith("audit/member4/") for name in changed):
        raise SystemExit("Baseline mismatch; audit stopped.")
    tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    production = {name: digest(ROOT / name) for name in tracked if not name.startswith("audit/")}
    generated = {
        path.relative_to(ROOT).as_posix(): digest(path)
        for path in (ROOT / "retrieval/vector_store/data").glob("*") if path.is_file()
    }
    cfg = dotenv_values(ROOT / ".env")
    versions = {}
    for name in ["fastapi", "starlette", "pydantic", "PyJWT", "bcrypt", "openai", "groq", "google-genai", "sentence-transformers", "faiss-cpu", "numpy", "PyMuPDF", "streamlit", "httpx", "requests"]:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "not installed"
    environment = {
        "captured_at": now(), "audited_commit": BASELINE, "execution_head": head,
        "python": platform.python_version(), "platform": platform.platform(),
        "packages": versions, "production_hashes_before": production,
        "vector_store_hashes_before": generated,
        "configuration": {
            "use_mock_agents": cfg.get("USE_MOCK_AGENTS", "unset"),
            "agent1_model": cfg.get("AGENT1_OPENROUTER_MODEL", "default"),
            "agent2_model": cfg.get("OPENROUTER_MODEL", "default"),
            "agent3_model": cfg.get("GROQ_MODEL", "default"),
            "provider_key_configured": {name: bool(cfg.get(name)) for name in ["AGENT1_OPENROUTER_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "GROQ_API_KEY"]},
        },
    }
    save_json("environment.json", environment)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8", HF_HUB_OFFLINE="1")
    commands = [
        [sys.executable, "-m", "tests.test_rules_no_api"],
        [sys.executable, "-m", "unittest", "tests.test_integration", "-v"],
        [sys.executable, "-m", "unittest", "tests.test_rag_evidence", "tests.test_decision_safety", "tests.test_faiss_build", "-v"],
    ]
    records, logs = [], []
    for command in commands:
        run = subprocess.run(command, cwd=ROOT, env=env, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=180)
        label = ".venv/Scripts/python.exe " + " ".join(command[1:])
        output = sanitize(run.stdout + run.stderr)
        records.append({"command": label, "exit_code": run.returncode})
        logs.append(f"COMMAND: {label}\nEXIT CODE: {run.returncode}\n{output}")
        print(label, "exit", run.returncode, flush=True)
    log_dir = AUDIT / "evidence" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "baseline-tests.txt").write_text("\n\n".join(logs), encoding="utf-8")
    save_json("baseline-tests.json", {"executed_at": now(), "runs": records})


if __name__ == "__main__":
    main()
