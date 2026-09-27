# IR-09: live claim-to-source verification

**Not Executed - Environmental Limitation.** The configured Agent 1 and Agent 2 OpenRouter attempts returned HTTP 401. No live generated Agent 2 answer with `grounded=True` was obtained. Therefore no live factual claims can honestly be labelled Supported, Partially supported or Unsupported.

Evidence: `json/IR-01-retrieval.json` records both provider rejections. `json/IR-12-http.json` records the resulting live public-pipeline failure. Later live attempts were skipped after the rejection.

IR-10 independently verified actual chunk/file/page traceability. That does not substitute for checking claims in an answer. IR-24 supplies a separate, deliberately unsupported provider-response fixture: its claim references `[1]`, which maps to the first retained IR-01 passage, `who_un_environment_guidance_p153_c01`, file `who_un_environment_guidance.pdf`, PDF page 153. The page concerns exposure routes/open dumping and municipal disposal of healthcare waste; it does not contain the fixture's invented 17-hour legal rule. The fixture claim is **Unsupported** and the runtime returned `grounded=True`. This is evidence of a missing application-level verification gate, not evidence that the live model fabricated that rule.

To complete IR-09 later, obtain a successful live answer using locally repaired provider access, preserve its unedited JSON, and make a table with claim, citation number, chunk ID, filename, PDF page, supporting passage and Supported/Partially supported/Unsupported judgement. Do not retrofit that later result into this dated run.
