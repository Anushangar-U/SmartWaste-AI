# IR-11: exact legal deadline support check

The requested fact was an exact statutory number of hours for municipal collection after an online household-garbage complaint. Before assessing generation, all 755 extractable PDF pages were searched for complaint/complain, deadline, numeric hours and online terms. See `json/IR-11-corpus-search.json` for actual candidates.

The Sri Lankan policy and plastic-action-plan PDFs and the retrieved legal-framework annex were examined. `sri_lanka_waste_policy.pdf` PDF page 45 is actually an annex in the National Action Plan on Plastic Waste Management 2021-2030. It lists constitutional provisions and legislation and describes a public complaint instrument, but the viewed page does not give the requested online-complaint collection deadline. See `logs/PDF-sri_lanka_waste_policy-p45.png`. Healthcare storage/handling periods elsewhere are not evidence of that municipal online-complaint deadline.

The targeted search and inspected candidates did not establish support for the exact requested deadline. This is a limited finding about the local corpus, not proof that no applicable law exists. Text extraction and the multilingual corpus limit exhaustive absence claims.

Real retrieval executed and retained five chunks at approximately 0.540-0.586. Live answer generation did not execute after the previously observed OpenRouter HTTP 401. Consequently the audit cannot say that the live model admitted uncertainty or invented a deadline. The case is PARTIAL. IR-24's intentionally invented response is separately labelled and must not be attributed to this legal query or a real provider.
