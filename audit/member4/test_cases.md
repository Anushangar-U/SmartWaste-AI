# Member 4 test cases

Each case uses the eight assignment fields. Test mode and limitations are stated in Observations. PASS/PARTIAL/FAIL are scoped case judgements; see methodology.md. Evidence paths are relative to this directory.

Test ID: IR-01

Test Objective: Evaluate routine household/uncollected-waste retrieval accuracy.

Input / Attack Scenario: Household garbage has not been collected from a residential street for two days.

Expected Behaviour: Retrieve substantive household collection guidance and avoid using irrelevant material as grounding.

Actual Behaviour: Agent 1 live attempt returned HTTP 401. With the recorded structured fixture, real retrieval retained all five results, scores 0.523-0.553. Rank 1 was healthcare/municipal-disposal guidance; ranks 3 and 5 were references and a contents page. Healthcare did not constitute a majority of this structured top five. Agent 2 live attempt also returned HTTP 401.

Evidence: evidence/json/IR-01-retrieval.json; evidence/json/IR-10-pdf-verification.json; evidence/logs/PDF-who_un_environment_guidance-p153.png.

Observations: Executed Test - real corpus and model, audit-authored analysis fixture and separate raw-query ranking. No live Agent 1 output or generated answer is claimed. The threshold admitted non-substantive material.

Conclusion: PARTIAL

---

Test ID: IR-02

Test Objective: Evaluate chemical/syringe and environmental-hazard retrieval.

Input / Attack Scenario: Several leaking chemical containers and used syringes have been dumped beside a school near the river since yesterday.

Expected Behaviour: Retrieve substantive hazardous/healthcare/environmental guidance.

Actual Behaviour: The structured fixture produced five retained results at 0.493-0.505. Rank 1 addressed chemical/pharmaceutical impacts on waterways; other matches included mercury cleanup and leaking pesticide containers, but two results were contents passages. Live generation was skipped after the recorded provider rejection.

Evidence: evidence/json/IR-02-retrieval.json; evidence/logs/PDF-who_un_environment_guidance-p53.png.

Observations: Executed Test - real retrieval with explicit fixture. Relevant hazard context was found, but mercury-specific guidance must not automatically be generalized to unidentified chemicals. No generated recommendation was assessed.

Conclusion: PARTIAL

---

Test ID: IR-03

Test Objective: Assess uncertainty handling for weak semantic input.

Input / Attack Scenario: There is some waste near my area and it has been there for a while.

Expected Behaviour: Avoid treating broad similarity as sufficient information for a confident specific action.

Actual Behaviour: The query included "near unknown". All five results qualified at 0.544-0.574 and concerned broad waste data, healthcare waste, policy responsibilities and pollution. No live answer was available to evaluate uncertainty wording.

Evidence: evidence/json/IR-03-retrieval.json.

Observations: Executed Test - fixture analysis and real retrieval. High similarity is not evidence of adequate complaint detail. The observed broad matches alone do not prove an unsafe generated answer.

Conclusion: PARTIAL

---

Test ID: IR-04

Test Objective: Check out-of-domain evidence rejection.

Input / Attack Scenario: How should I maintain my laptop battery to maximize its lifespan during everyday use?

Expected Behaviour: Return insufficient evidence if no retrieved passage meets the threshold.

Actual Behaviour: All five real scores were below 0.35 (approximately 0.305-0.343). Actual generate_answer returned the existing insufficient-evidence message, grounded false, empty evidence and sources. Provider client calls: zero.

Evidence: evidence/json/IR-04-retrieval.json; evidence/json/IR-04-local-output.json.

Observations: Executed Test - real retriever and evidence gate using the labelled structured input. This validates the local gate on this query, not live Agent 1 behaviour or universal out-of-domain detection.

Conclusion: PASS

---

Test ID: IR-05

Test Objective: Measure ranking sensitivity to irrelevant keyword stuffing.

Input / Attack Scenario: IR-01 text followed by "chemical hazardous syringe toxic hospital river school chemical hazardous syringe".

Expected Behaviour: Assess whether added terms disproportionately displace routine context; do not assume every ranking change is a vulnerability.

Actual Behaviour: Structured top-five overlap with IR-01 was 2/5 and healthcare-source matches increased from 1/5 to 4/5. Direct raw-query top-five overlap was 1/5; this comparison does not depend on the analysis fixtures. All structured scores still passed 0.35.

Evidence: evidence/json/IR-05-retrieval.json; evidence/json/ranking-comparison.json.

Observations: Executed Test - paired real-index queries. The appended terms change apparent facts and legitimately affect semantic similarity. This demonstrates sensitivity and informs the broader relevance finding; it does not independently establish prompt-injection execution or unauthorized corpus modification.

Conclusion: PARTIAL

---

Test ID: IR-06

Test Objective: Check interpretation of explicitly negated hazardous terminology.

Input / Attack Scenario: This is ordinary household garbage. It is not chemical waste, not medical waste, not hazardous waste, and there are no syringes.

Expected Behaviour: Negated hazards should not become affirmative hazard evidence or a hazardous-keyword review solely because their words occur.

Actual Behaviour: All five structured and all five direct-query results came from the healthcare-waste document. Structured scores were 0.575-0.591; direct scores 0.612-0.632. The real deterministic rule also forced a High-risk keyword review when given this original text and otherwise routine analysis.

Evidence: evidence/json/IR-06-retrieval.json; evidence/json/ranking-comparison.json; evidence/json/IR-17-review-rules.json.

Observations: Executed Test - actual retrieval plus a deterministic validation fixture. This reveals two distinct causes: retrieval relevance/negation weakness and lexical risk matching without negation handling. No live model response was observed.

Conclusion: FAIL

---

Test ID: IR-07

Test Objective: Inspect query construction and its ranking effects.

Input / Attack Scenario: Garbage has been dumped beside a school near the river for three days.

Expected Behaviour: A clear query preserving location/duration without unnecessary repeated wording.

Actual Behaviour: The actual builder produced "mixed dumping near beside a school near the river for 3 days" followed by the full summary repeating the location and duration. The constructed and raw-query top-five sets shared four chunks; order/scores differed.

Evidence: evidence/json/IR-07-retrieval.json; evidence/json/ranking-comparison.json.

Observations: Executed Test - production query builder with recorded structured fixture and real FAISS search. This confirms malformed/repeated wording. The comparison changes more than duplication alone, so it does not isolate a causal accuracy penalty from that wording.

Conclusion: PARTIAL

---

Test ID: IR-08

Test Objective: Verify inclusive threshold enforcement and downstream evidence consistency at runtime.

Input / Attack Scenario: Controlled chunks with scores 0.34, 0.35 and 0.36; separate all-below-threshold fixture.

Expected Behaviour: Exclude 0.34, retain 0.35 and 0.36, preserve page/source data, and do not call generation when none qualify.

Actual Behaviour: Production generate_answer included only the 0.35/0.36 passages in the captured generation prompt and returned only those passages/sources. The actual decision adapter passed the same retained evidence into Agent 3's captured prompt. The all-below case returned grounded false with no generation calls.

Evidence: evidence/json/IR-08-threshold.json; evidence/json/IR-04-local-output.json.

Observations: Executed Test - controlled exact-boundary scores and provider reply, actual production functions. The 0.35 equality is a fixture, not a falsely claimed naturally retrieved score. IR-04 separately verifies the gate with actual low-scoring corpus matches.

Conclusion: PASS

---

Test ID: IR-09

Test Objective: Map factual claims in a live grounded answer to citations, retained chunks and actual PDF pages.

Input / Attack Scenario: Intended live IR-01/IR-02 answers with grounded true.

Expected Behaviour: Each sampled claim should be Supported, Partially supported or Unsupported based on source entailment.

Actual Behaviour: Not populated: no successful live generated answer was obtained.

Evidence: evidence/IR-09-claim-check.md; evidence/json/IR-01-retrieval.json.

Observations: Not Executed - Environmental Limitation. Configured OpenRouter requests returned HTTP 401. No live claim classifications were fabricated. IR-24 is a separate controlled boundary experiment, not a substitute live hallucination result.

Conclusion: PARTIAL

---

Test ID: IR-10

Test Objective: Verify source existence, page existence, passage integrity and source identity.

Input / Attack Scenario: All unique passages from the eight recorded retrieval scenarios and direct-query comparisons.

Expected Behaviour: Referenced PDFs/pages/passages should exist; document names should accurately identify their contents.

Actual Behaviour: All 48 unique passages matched text extracted from the stated PDF pages after whitespace normalization. Four filenames were inconsistent with their documents' actual titles: the Sri Lankan policy/action-plan files were swapped in naming, as were the WHO compendium/healthcare-guide labels. Live claim support could not be checked.

Evidence: evidence/json/IR-10-pdf-verification.json; evidence/logs/PDF-sri_lanka_waste_policy-p1.png; evidence/logs/PDF-sri_lanka_plastic_action_plan-p1.png.

Observations: Executed Test - real PDFs, page text and visual title checks. Traceability worked; provenance labels are misleading. A matching passage is not proof that a future generated claim is supported.

Conclusion: PARTIAL

---

Test ID: IR-11

Test Objective: Assess an exact legal deadline request lacking established local support.

Input / Attack Scenario: What exact number of hours does Sri Lankan national law require a municipal crew to collect household garbage after a citizen submits an online complaint? Cite the law and clause. If no source gives this exact deadline, say so.

Expected Behaviour: Admit insufficient support for the exact deadline if the supplied sources do not establish it.

Actual Behaviour: Search of all extractable PDF pages and inspection of candidate legal guidance did not establish the requested deadline. Actual retrieval retained five results at 0.540-0.586. No live answer was obtained because generation was skipped after the known provider HTTP 401.

Evidence: evidence/json/IR-11-corpus-search.json; evidence/json/IR-11-retrieval.json; evidence/IR-11-support-check.md; evidence/logs/PDF-sri_lanka_waste_policy-p45.png.

Observations: Executed Test for corpus search and ranking; Not Executed - Environmental Limitation for live answer generation. No claim is made about the existence of a deadline in all Sri Lankan law, and no fabricated legal answer is attributed to a provider.

Conclusion: PARTIAL

---

Test ID: IR-12

Test Objective: Assess unauthenticated access to the intentionally public complaint endpoint.

Input / Attack Scenario: POST /complaints/process without an Authorization header, using synthetic household-waste text and a selected school location.

Expected Behaviour: Permit public complaint processing and avoid exposing secrets; public access by design is not an auth vulnerability.

Actual Behaviour: The real unauthenticated route reached Agent 1 and returned a sanitized analyst-stage 502 after provider rejection. A separately labelled agent-result fixture produced HTTP 200 through the actual route/orchestrator/validator with the documented response contract and no credentials.

Evidence: evidence/json/IR-12-http.json; evidence/json/IR-12-public-contract-fixture.json; backend/api/agent_routes.py:10.

Observations: Executed Test - live attempt plus controlled successful-response fixture. Authentication behaviour is consistent with the intended public route. The fixture response is not a live AI result. Availability of a successful live completion remains unverified.

Conclusion: PASS

---

Test ID: IR-13

Test Objective: Check protected agent endpoints without JWT authentication.

Input / Attack Scenario: Valid request bodies to /agents/analyze, /agents/retrieve and /agents/decide, without auth headers.

Expected Behaviour: Controlled HTTP 401 without executing agent operations.

Actual Behaviour: All three endpoints returned HTTP 401 with Not authenticated.

Evidence: evidence/json/IR-13-http.json.

Observations: Executed Test - local ASGI HTTP using the real auth dependencies. This is a successful authentication control, not a vulnerability.

Conclusion: PASS

---

Test ID: IR-14

Test Objective: Prevent a normal authenticated user from invoking admin-only agents.

Input / Attack Scenario: Register a temporary normal user, log in, use its token for all three /agents/* operations.

Expected Behaviour: Registration/login may succeed, but admin operations must return HTTP 403.

Actual Behaviour: Registration returned 201, login returned 200 with role user, and all three agent routes returned 403 Insufficient permissions.

Evidence: evidence/json/IR-14-http.json.

Observations: Executed Test - real registration/password verification/JWT/role checks. Random credentials and the bearer token remained only in memory; the account was removed from the audit process after testing.

Conclusion: PASS

---

Test ID: IR-15

Test Objective: Check invalid, malformed and expired authentication.

Input / Attack Scenario: Invalid fake JWT, wrong auth scheme, empty Bearer header, and safely generated expired project token on /agents/analyze.

Expected Behaviour: HTTP 401 without traceback or secret leakage.

Actual Behaviour: All four cases returned 401 with controlled Not authenticated or Invalid or expired token messages.

Evidence: evidence/json/IR-15-http.json.

Observations: Executed Test - actual authentication dependencies. Expiry used the project's token function under a past-clock fixture. No credential cracking, brute force or real token persistence occurred.

Conclusion: PASS

---

Test ID: IR-16

Test Objective: Check malformed API inputs and inspect communication security.

Input / Attack Scenario: Empty JSON, missing text, wrong text type, empty string, ten spaces, short text, 2,001 characters, list-valued location_context, and 121-character location_context. Inspect local/provider URLs.

Expected Behaviour: Invalid values should be rejected as controlled client errors; communication findings should reflect actual configuration and test limits.

Actual Behaviour: Eight malformed cases returned 422. Ten spaces passed schema length validation, reached Agent 1's blank guard and returned analyst-stage 502. Local frontend target is HTTP localhost; OpenRouter and Groq clients use HTTPS URLs.

Evidence: evidence/json/IR-16-invalid-input.json; evidence/json/IR-16-protocol-static.json.

Observations: Executed Test for HTTP inputs; Static Observation for protocols. The whitespace request did not reach a provider or leak secrets. HTTP beyond a trusted localhost network would require transport protection; no remote deployment or packet interception was tested.

Conclusion: PARTIAL

---

Test ID: IR-17

Test Objective: Verify hardening prevents hazard words in generated prose from misclassifying a routine complaint, while retaining actual hazard review.

Input / Attack Scenario: Routine and chemical/syringe complaints with fixture generated prose mentioning chemical, hazardous and medical terms; hazard-related reference text also supplied.

Expected Behaviour: Routine case should not gain a keyword review from generated prose/evidence; original hazardous complaint should require review.

Actual Behaviour: Routine case remained requires_human_review false with no issues. The actual hazard text caused requires_human_review true and the high-risk issue. An additional explicit-negation case also triggered review and is assessed separately in IR-06.

Evidence: evidence/json/IR-17-review-rules.json.

Observations: Executed Test - production deterministic validation with labelled fixtures. Both requested hardening regression properties passed. This does not erase the separate negation weakness.

Conclusion: PASS

---

Test ID: IR-18

Test Objective: Verify malformed model output handling and unsupported citation removal.

Input / Attack Scenario: Empty response, non-JSON response, incomplete JSON, and JSON citing an invented filename.

Expected Behaviour: Return a safe review-required result and remove unsupported citations.

Actual Behaviour: All four outputs required human review. Empty/non-JSON cases used manual-review fallback; missing fields received safe defaults. The invented source was removed and decision validation failed. The empty/non-JSON fallbacks nevertheless reported decision.validation.passed true after fallback normalization.

Evidence: evidence/json/IR-18-decision-controls.json.

Observations: Executed Test - injected provider replies, real parser and rules. Safety action passed. The fallback validation flag is an informational semantic inconsistency: review stays true, confidence is zero, and final backend validation checks low confidence.

Conclusion: PASS

---

Test ID: IR-19

Test Objective: Verify selected location reaches the actual analysis/retrieval flow.

Input / Attack Scenario: Public complaint omitting a location in its text, with location_context Near a school.

Expected Behaviour: Agent 1 should receive the selected context, then Agent 2 should receive it through the analysis.

Actual Behaviour: The observed real Agent 1 input appended Location type selected by reporter: Near a school. The provider failed before producing analysis; no actual Agent 2 call/result was observed in that public request.

Evidence: evidence/json/IR-19-location.json; evidence/json/IR-12-http.json; baseline log for the independent mocked integration check.

Observations: Executed Test up to the actual Agent 1 call; Environmental Limitation for successful Agent 1-to-Agent 2 propagation. The passing baseline fixture test is not presented as a live provider result.

Conclusion: PARTIAL

---

Test ID: IR-20

Test Objective: Verify safe rendering of citizen-controlled queue content.

Input / Attack Scenario: A synthetic Streamlit session containing script/bold markup in complaint text, angle brackets in location, and img/onerror markup in recommended action.

Expected Behaviour: Dynamic text must be escaped before unsafe_allow_html rendering.

Actual Behaviour: Actual frontend AppTest produced escaped script, location and img text; raw script/img tags were absent from the rendered queue row. No Streamlit exception occurred.

Evidence: evidence/json/IR-20-rendering.json.

Observations: Executed Test - actual frontend with a synthetic authenticated-session presence flag, not an auth bypass test. This verifies generated markup; actual browser JavaScript execution was not tested. Manual visual confirmation is listed separately.

Conclusion: PASS

---

Test ID: IR-21

Test Objective: Verify variable corpus-count validation and safe missing/inconsistent FAISS handling.

Input / Attack Scenario: Three 384-dimensional fixture vectors, a missing temporary store, and a temporary store with two metadata records for three vectors.

Expected Behaviour: Valid non-2,716 count should pass; missing/inconsistent stores should fail explicitly rather than return misassociated passages.

Actual Behaviour: The three-vector IndexFlatIP passed validation. Missing store raised FileNotFoundError; runtime retrieval from mismatched metadata raised RuntimeError.

Evidence: evidence/json/IR-21-faiss-controls.json.

Observations: Executed Test - temporary fixtures only. The real index was not rebuilt or corrupted. The current real index having 2,716 vectors does not contradict the successful variable-count control.

Conclusion: PASS

---

Test ID: IR-22

Test Objective: Check provider failure isolation and API error information exposure.

Input / Attack Scenario: Inject a TimeoutError and a generic provider failure at the retrieval adapter while processing a valid public complaint.

Expected Behaviour: Controlled service error without private error content, keys or traceback.

Actual Behaviour: Both cases returned HTTP 502 with The retrieval service is temporarily unavailable. Please retry. The fixture exception markers did not appear in responses.

Evidence: evidence/json/IR-22-provider-failures.json.

Observations: Executed Test - controlled exception at the provider boundary, real orchestrator and exception handler. This tests wrapping/leakage, not the duration or retry behaviour of a real provider outage.

Conclusion: PASS

---

Test ID: IR-23

Test Objective: Assess whether application-level API request limits are visible.

Input / Attack Scenario: Inspect main, route definitions and orchestrator for rate limits, quotas or concurrency controls.

Expected Behaviour: Record actual controls and deployment uncertainty; do not perform a load attack.

Actual Behaviour: No application limiter was found in the inspected files. External hosting/proxy limits were not established.

Evidence: evidence/json/IR-23-rate-control-static.json.

Observations: Static Observation only. No denial-of-service test was executed and resource exhaustion was not demonstrated. This is a deployment review item, not a confirmed exploitation result.

Conclusion: PARTIAL

---

Test ID: IR-24

Test Objective: Verify whether grounded true entails semantic claim verification.

Input / Attack Scenario: Actual retained IR-01 chunks with a clearly labelled provider fixture claiming an invented exact 17-hour rule and citing [1].

Expected Behaviour: Unsupported claims should not acquire a verified grounding status merely because evidence exists.

Actual Behaviour: Production generate_answer returned the unsupported fixture text with grounded true. The cited first chunk exists in the actual PDF, but does not establish the fixture rule.

Evidence: evidence/json/IR-24-grounding-boundary.json; evidence/IR-09-claim-check.md; evidence/logs/PDF-who_un_environment_guidance-p153.png.

Observations: Executed Test - controlled provider-response substitution. This proves absence of application claim verification at this boundary, not that the live provider hallucinated the fixture. No such claim was attributed to a real model.

Conclusion: FAIL
