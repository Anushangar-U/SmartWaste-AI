# SmartWaste-AI

SmartWaste-AI is a three-agent decision-support system for waste complaints:

1. Agent 1 uses Gemini to convert a complaint into structured waste analysis.
2. Agent 2 retrieves evidence from the local FAISS knowledge base and uses OpenRouter to produce a grounded summary.
3. Agent 3 uses Groq to recommend a priority and action, followed by deterministic safety validation.

The FastAPI backend orchestrates the agents. The Streamlit frontend provides a public complaint form and an authenticated staff review view. AI recommendations are decision support only; high-risk, critical, uncertain, and low-confidence cases require authorized human review.

## Setup

Create a local `.env` from `.env.example` and replace every placeholder locally. Never commit `.env` or real credentials.

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

For a no-API demo, set `USE_MOCK_AGENTS=true`. For the real three-agent pipeline, set it to `false` and configure the Gemini, OpenRouter, and Groq keys.

## Rebuild the FAISS knowledge base

Generated FAISS files are intentionally ignored by Git. Build `retrieval/vector_store/data/smartwaste.faiss` and `retrieval/vector_store/data/metadata.json` from the committed PDFs with:

```bash
python -m retrieval.vector_store.faiss_store
```

The command runs PDF ingestion, chunking, MiniLM embedding, FAISS indexing, persistence, and validation.

## Run

Start the backend:

```bash
python -m uvicorn backend.main:app --reload
```

Start the frontend in another terminal:

```bash
python -m streamlit run frontend/app.py
```

Public complaints are submitted to `POST /complaints/process` without authentication. Authentication is required for staff access and for the individual `/agents/*` debugging endpoints.

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
python tests/test_rules_no_api.py
python -m unittest tests.test_integration -v
```

`tests/test_waste_analyzer.py` is a manual Gemini smoke test and requires a configured Gemini key.
