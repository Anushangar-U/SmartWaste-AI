# IT3041 report outline - Member 4

This is report-support material, not a fabricated personal submission. Add your name, student ID and assignment formatting yourself. Retain the evidence limitations when adapting it.

## 1. Executive Summary

SmartWaste AI was assessed at commit `2a8615c2b24b5c75ab024de8af4525e2f428f165` on 27 September 2026. The assessment covered retrieval reliability/manipulation, grounding, provenance, authentication, authorization, APIs and protocols. Production code was not modified.

The independent baseline passed 24 automated tests. Of 24 designed audit cases, 22 ran dynamically at least in part, one was static-only and one could not execute. Conclusions were 11 PASS, 11 PARTIAL and 2 FAIL. Four root-cause findings were documented: two Medium information-integrity weaknesses and two Low precision/provenance weaknesses. Passing controls included evidence thresholding, JWT/role rejection, safe rendering, malformed-output review, source-name rejection and index consistency checks.

Both configured OpenRouter paths returned HTTP 401, preventing successful live analysis and generated-answer evaluation. Real FAISS/PDF tests and explicitly labelled fixtures still established local control behaviour. No successful live hallucination, auth bypass or remote-network exploit was demonstrated.

## 2. Scope of Testing

### System evaluated

The final merged SmartWaste AI code, existing MiniLM/FAISS index, five local knowledge PDFs, FastAPI API/authentication and Streamlit frontend. Audited baseline and artifact hashes are in environment.md and evidence/json/environment.json.

### Assigned specialization

Student 4: Retrieval Accuracy; Retrieval Manipulation; Hallucination due to Retrieval; Source Reliability; Authentication; Authorization; API Security; Communication Protocol Security.

### Components evaluated

Agent 1 input/adapter path; Agent 2 query builder, real retriever and evidence filter; Agent 2 generation boundary; Agent 3 parser/safety controls; API authentication and authorization; malformed input/error handling; Streamlit queue rendering; index build validation and PDF traceability. See architecture.md for code references.

### Scope limitations

OpenRouter HTTP 401 prevented live answer claims from being checked. Structured retrieval fixtures are not live Agent 1 outputs. TestClient is local in-process ASGI; AppTest inspects Streamlit-generated markup, not browser script execution. Protocol claims are static; external infrastructure and DoS resistance were not tested. Corpus phrase searching cannot prove the absence of a rule from all law. Real store build history lacks a manifest. No mitigation or production redesign was authorized.

## 3. Evaluation Methodology

### Methodology

Verify exact baseline; inspect actual architecture; run existing tests; execute targeted benign/adversarial cases; save sanitized evidence; assess causes and severity only after observing results; verify production integrity; commit audit artifacts separately.

### Process

Use the eight-field cases in test_cases.md. Mark each component of a case as executed, static or environmentally blocked. Compare keyword-stuffed/negated text with ordinary text using both constructed and raw queries. Check threshold boundaries independently from semantic relevance. Trace sampled chunks to actual PDFs. Treat explicit provider fixtures as boundary-control experiments.

### Tools

Git; Python unittest; SentenceTransformer/MiniLM; FAISS; PyMuPDF extraction/rendering; FastAPI TestClient; Streamlit AppTest; unittest.mock for labelled fixtures; cryptographic file hashes and redaction helpers. No third-party system was attacked.

### Environment

Windows 11, Python 3.13.9, existing project virtual environment; installed package versions in environment.md. Local backend URL HTTP localhost; provider endpoints HTTPS. Credentials are never reproduced in the report.

### Evaluation criteria

PASS = observed expected control; PARTIAL = mixed result, static-only evidence or an incomplete stage; FAIL = executed contradiction. Risk is Impact + Likelihood -> Severity. Test cases are not vulnerability counts. Human review, disclaimers and the absence of autonomous action constrain impact ratings.

## 4. Test Cases Performed

Use test_cases.md without removing its limitations. Summarize the 24 cases with the table in results.md. Include selected evidence extracts: IR-08 filtered prompt/output; IR-13/14/15 HTTP rejection statuses; IR-20 escaped markup; IR-21 three-vector validation; IR-06 negation matches; IR-10 actual PDF titles.

Explicitly state that IR-09 was not executed and IR-11's live generation stage was blocked. Add only screenshots personally captured following evidence/screenshot-checklist.md. The five supplied PDF renders are generated source-page evidence, not screenshots of a live application.

## 5. Vulnerabilities Identified

| ID | Finding | Main evidence |
|---|---|---|
| M4-V01 | Relevance-poor context passes the similarity gate | IR-01, IR-06 and ranking-comparison JSON |
| M4-V02 | Grounded flag does not verify claim support | IR-24 controlled provider response, with actual cited PDF page |
| M4-V03 | Negated hazards trigger keyword review | IR-17 explicit-negation case, assessed in IR-06 |
| M4-V04 | Corpus filenames misidentify documents | IR-10 title text and source-page renders |

Use risk_register.md for full descriptions/root causes. Do not call the intentionally public complaint route a missing-auth vulnerability. Do not claim that a live model produced IR-24's fixture. Include successful controls to show the balanced assessment.

## 6. Risk Assessment

M4-V01 and M4-V02: Medium, because context/grounding integrity could mislead decision support, while autonomous harm and live hallucination prevalence were not demonstrated. M4-V03 and M4-V04: Low, because unnecessary review and inaccurate source labels have bounded demonstrated impact. There are no Critical or High findings from this evidence.

Discuss informational observations separately: local HTTP deployment conditions, whitespace classified as a service error, missing application limits in inspected code, fallback validation flag semantics, and missing historical index manifest. No load/interception attack was conducted.

## 7. Mitigation Strategies

Recommendations only: evaluate and curate retrieval quality; remove contents/reference-only chunks; assess reranking and metadata filters; calibrate thresholds rather than guessing; distinguish evidence availability from verified grounding; validate citations/claim entailment; improve negation handling conservatively; maintain verified document title/version metadata. Address input normalization, transport protection and request budgets in later authorized development.

Re-test any future mitigation on the same cases plus independent holdout inputs. Retain recall for real hazardous complaints. Do not treat more abstentions as an automatic quality improvement. No mitigation was implemented in this audit branch.

## 8. Reflection

Complete these prompts personally. No personal experience or learning claim has been written on your behalf.

### Challenges

- How did the provider HTTP 401 affect the claims you could make?
- How did you distinguish a controlled fixture from a real model response?
- Which PDF/source identity checks were difficult to interpret?

### Lessons learned

- What did you learn from controls that passed rather than failed?
- How would you explain similarity, relevance and factual support as different properties?
- How did you decide what counted as a vulnerability versus an observation?

### Future improvements

- Which live tests would you complete after authorized provider access is restored?
- What additional complaints/languages would improve the retrieval evaluation?
- How would you validate proposed mitigations without weakening human-review safety?
