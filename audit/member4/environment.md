# Audited environment

## Git baseline

Initial branch: `improvement/final-hardening`, commit `eff184ef36bb6106fd826c638fc1de9bd44a26a3`, clean working tree. The repository root and origin were verified as `C:\visual studio files\SmartWaste-AI-integrated` and `https://github.com/Anushangar-U/SmartWaste-AI.git`.

After `git fetch origin`, `origin/main` was exactly the required `2a8615c2b24b5c75ab024de8af4525e2f428f165` (merge PR #12). Local `main` was switched to and updated with `git pull --ff-only origin main`. The new branch `audit/member4-ir-security` was created from that exact commit. No pre-existing changes needed preserving. No force-push or merge was performed.

## Runtime

Windows 11, build 26200; Python 3.13.9 in the existing `.venv`. The sandbox could not directly execute its base interpreter, so the authorized audit commands ran with the required execution permission. No packages were installed or upgraded.

| Package | Observed version |
|---|---|
| FastAPI / Starlette | 0.141.1 / 1.6.0 |
| Pydantic / PyJWT / bcrypt | 2.13.5 / 2.14.0 / 5.0.0 |
| OpenAI SDK / Groq SDK / Google GenAI | 3.16.2 / 1.7.0 / 2.24.0 |
| sentence-transformers / faiss-cpu | 6.1.0 / 1.15.1 |
| NumPy / PyMuPDF | 2.5.3 / 1.28.2 |
| Streamlit / httpx / requests | 1.64.0 / 0.28.1 / 2.34.2 |

Evidence: [environment.json](evidence/json/environment.json). The report relies on the observed installed versions, not the unpinned requirements file.

## Configuration and local assets

`USE_MOCK_AGENTS=false` was observed. Provider key presence was recorded as booleans only. Configured model names were Agent 1 `nex-agi/nex-n2.5-mini:free`, Agent 2 `openrouter/free`, and Agent 3 `openai/gpt-oss-120b`. The local frontend target was `http://localhost:8000`. JWT configuration used HS256 with a 60-minute expiry. No secrets are included here.

The existing store contained 2,716 vectors and matching metadata records, dimension 384, `IndexFlatIP`. `build_info.json` was absent; therefore the historical model revision and build settings of this pre-existing index cannot be independently reconstructed from a manifest. The source code uses MiniLM and the expected dimension, and sampled passages matched the current PDFs. File hashes record exactly which local store was tested.

Five PDFs were present, with 755 total PDF pages: 116, 200, 60, 50 and 329 respectively in filename order. Text extraction searched all these pages. Extracted-text limitations and font encoding errors mean a failed phrase search is not proof that a rule is absent from all law or all source images.

## Independent baseline execution

| README command | Result |
|---|---|
| `python -m tests.test_rules_no_api` | Exit 0; seven manual-output examples inspected; this script has no assertions |
| `python -m unittest tests.test_integration -v` | 9 tests, OK |
| `python -m unittest tests.test_rag_evidence tests.test_decision_safety tests.test_faiss_build -v` | 15 tests, OK |

Total: 24 automated tests passed in this audit's own run, before adversarial tests. [Sanitized log](evidence/logs/baseline-tests.txt).

## Environmental limitation

Live Agent 1 OpenRouter and Agent 2 OpenRouter attempts returned `AuthenticationError`, HTTP 401. The audit did not reveal the reason beyond that status, attempt to repair keys, switch providers, or claim that rejected calls generated answers. The live public request consequently returned an analyst-stage HTTP 502. Later live generation was skipped after that rejection; no live Groq completion was reached by the public pipeline.

API tests used FastAPI `TestClient` in-process ASGI requests, not a listening network server. Streamlit rendering used `AppTest`, not a real browser. Protocol findings are static observations, not packet captures. These distinctions limit the conclusions and are repeated in the affected cases.
