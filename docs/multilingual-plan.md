# Multilingual preparation (design only)

No Sinhala or Tamil support is claimed by this release. The English MiniLM model and
three-agent production flow are unchanged. There is no reviewed multilingual benchmark.

## Preserve provenance

The database already retains original complaint text separately from extracted analysis.
A future additive migration can add explicitly supplied language, a translated working
copy, translation provider/model/version and review status. Never overwrite original text.
Show original and translated text together to bilingual staff and explain any external
translation processing to citizens. Do not infer ethnicity or other personal traits.

## Two options to evaluate

1. Translate to English for the existing pipeline, preserve original text, and translate
   safe public status/clarification messages separately. Use approved translations for
   fixed UI strings. Hazard terms, negation, locations and time expressions need special
   evaluation; a fluent translation can still change meaning.
2. Evaluate a multilingual embedding model against the same language-specific reference
   queries. A changed model requires a separately versioned index and compatible query
   embeddings, even if dimensions happen to match. Retain the English baseline and do not
   overwrite the existing index until an evaluated migration is approved.

## Acceptance before enabling a language

- Native-language reviewers annotate Sinhala, Tamil and English complaints independently.
- Include mixed-language input, transliteration, colloquial terms, denied/uncertain hazards,
  location names and unknown duration. Keep paraphrase families out of both train/tuning
  and held-out evaluation simultaneously.
- Report extraction accuracy, retrieval relevance, hazardous-case misses, unnecessary
  review, supported claims, latency and provider failures by language with denominators.
- Evaluate translated clarification questions for meaning and safe behavior.
- Unsupported or uncertain translations enter staff review; no silent confident fallback.
- Human reviewers establish acceptance criteria before looking at held-out scores.

This phase deliberately adds documentation only. Translation, language detection and a
replacement embedding model require separately authorized and reviewed implementation.
