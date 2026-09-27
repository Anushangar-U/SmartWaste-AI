# SmartWaste-AI

SmartWaste-AI is a three-agent decision-support system for waste complaints:

1. Agent 1 uses OpenRouter when `AGENT1_OPENROUTER_API_KEY` is set, with Gemini as an optional fallback, to convert a complaint into structured waste analysis.
2. Agent 2 retrieves evidence from the local FAISS knowledge base and uses OpenRouter to produce a grounded summary.
3. Agent 3 uses Groq to recommend a priority and action, followed by deterministic safety validation.

The FastAPI backend orchestrates the agents. The Streamlit frontend provides a public complaint form and an authenticated staff review view. AI recommendations are decision support only; high-risk, critical, uncertain, and low-confidence cases require authorized human review.

## Setup

Create a local `.env` from `.env.example` and replace every placeholder locally. Never commit `.env` or real credentials.

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

For a no-API demo, set `USE_MOCK_AGENTS=true`. For the real three-agent pipeline, set it to `false` and configure Agent 1 with `AGENT1_OPENROUTER_API_KEY` (or `GEMINI_API_KEY` as a fallback), Agent 2 with `OPENROUTER_API_KEY`, and Agent 3 with `GROQ_API_KEY`. Agent 1 prefers OpenRouter when both Agent 1 provider keys are present. Model names are configurable: the example uses `nex-agi/nex-n2.5-mini:free`, `openrouter/free`, and `openai/gpt-oss-120b`; available OpenRouter routing and models can vary.

## Rebuild the FAISS knowledge base

Generated FAISS files are intentionally ignored by Git. Build `retrieval/vector_store/data/smartwaste.faiss` and `retrieval/vector_store/data/metadata.json` from the committed PDFs with:

```bash
python -m retrieval.vector_store.faiss_store
```

The command runs PDF ingestion, chunking, MiniLM embedding, FAISS indexing, persistence, and validation. It also writes `retrieval/vector_store/data/build_info.json` with the model, chunk settings, dimension, and vector count.

## Run

Start the backend:

```bash
python -m uvicorn backend.main:app --reload
```

Start the frontend in another terminal:

```bash
python -m streamlit run frontend/app.py
```

Public complaints are submitted to `POST /complaints/process` without authentication. Its JSON body requires `text` and optionally accepts `location_context` from the location selector. Text-only clients remain supported. Authentication is required for staff access and for the individual `/agents/*` debugging endpoints.

## Response contract

The complaint endpoint returns:

```text
request_id
analysis
retrieval
  query, answer, grounded
  sources[]: source, page
  evidence[]: chunk_id, source, page, text, score
decision
  priority, recommended_action, explanation
  supporting_sources, requires_human_review, confidence, validation
validation
  passed, warnings
disclaimer
```

## Tests

Run deterministic tests without external API calls:

```bash
python -m tests.test_rules_no_api
python -m unittest tests.test_integration -v
python -m unittest tests.test_rag_evidence tests.test_decision_safety tests.test_faiss_build -v
```

`tests/test_waste_analyzer.py` is a manual Agent 1 provider smoke test and requires a configured Agent 1 API key.
