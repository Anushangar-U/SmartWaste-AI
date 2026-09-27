# Methodology and assessment criteria

The audit verified the exact requested Git baseline, inspected the implementation, ran the README baseline tests, then tested retrieval, API boundaries and hardening regressions. Only after inspecting results were related weaknesses grouped into findings. Production code and its configuration were not repaired.

## Evidence classes

1. **Executed Test - actual local assets:** MiniLM, the existing FAISS index, actual PDF extraction, and production functions executed locally.
2. **Executed Test - controlled fixture:** Explicitly substituted analysis inputs, provider replies or errors exercised production functions. These demonstrate a control's behaviour at a boundary. They do not demonstrate that a real provider emitted that reply.
3. **Executed Test - live attempt:** Configured OpenRouter requests were attempted with synthetic complaints. HTTP 401 is the actual result; no response content or successful generation is inferred.
4. **Static Observation:** Code/configuration inspection, including HTTP versus HTTPS and the absence of an application rate limiter in inspected files. No network exploitation is claimed.
5. **Not Executed - Environmental Limitation:** A required live claim-support assessment could not proceed because there was no live generated answer. Partly completed cases clearly state which substeps ran.

Audit SDK timeouts were bounded to 60 seconds and retries disabled only inside audit contexts. Original key values, SDK auth headers, secrets, login passwords and bearer tokens were never persisted. Temporary accounts were deleted from the audit process's memory. Temporary FAISS fixtures were created under the audit workspace and removed; the real store was hashed and preserved.

## Evaluation rules

PASS means the stated control worked on the observed inputs, within the documented test mode. PARTIAL means mixed relevance, a limited sub-result, a static-only assessment, or a required stage blocked by the environment. FAIL means the expected property was contradicted by executed evidence. PARTIAL is not automatically a vulnerability; no case conclusion estimates an exploit rate.

For retrieval accuracy, a passage is directly relevant when it gives substantive guidance on the complaint's waste/context. General environmental context is partial relevance. Tables of contents, reference lists and subject-mismatched passages are insufficient to justify specific recommendations even if their similarity score is high. These are qualitative labels on a small purposive sample, not a validated benchmark or population accuracy statistic.

Raw-query comparisons isolate semantic retrieval from audit-authored Agent 1 fixtures. The stuffed complaint changes some apparent factual content, so ranking change alone is not treated as an authentication or prompt-injection exploit. Explicit negation gives a stronger contradiction to examine. Similarity threshold enforcement is tested independently from whether the threshold is well calibrated.

Claim support requires mapping a claim to a valid citation, retained chunk, actual PDF and page, then assessing entailment. Passage existence alone is not enough. With no live generated answers, IR-09 remains unexecuted. IR-24 explicitly injects an unsupported provider answer to test whether the application validates it; it is not presented as a live hallucination.

PDF checks searched all extractable pages, verified 48 unique retrieved passages after whitespace normalization, and visually inspected five rendered pages. Actual document titles were checked against filenames. PDF page numbers are 1-based file pages, which differ from printed page numbers. The IR-11 search examined complaints/complain, deadlines, hours and online references, plus the retrieved legal-framework page. No legal advice or universal claim about Sri Lankan law is inferred from this corpus.

## Risk judgement

Risk is based on **Impact + Likelihood -> Severity**, using only Critical, High, Medium, Low or Informational. Impact considers the decision-support setting and mandatory review/disclaimers. Likelihood reflects reproducibility and input accessibility, not merely a hypothetical worst case. Model-hallucination frequency could not be measured. Reproducible information-integrity weaknesses can be findings even when no autonomous action occurs; documentation-only deployment concerns remain observations.

The four confirmed findings represent four root causes. Related test cases do not become separate vulnerabilities merely to increase the count. The report separately records successful controls, environmental limits and recommended mitigations; none of those mitigations were implemented.
