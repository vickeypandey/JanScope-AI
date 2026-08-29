# Evaluation report

Evaluation date: 25 August 2026  
Mode: deterministic demo mode  
Vector backend: ChromaDB with local hashing embeddings

## Measured smoke-dataset results

| Metric | Result |
|---|---:|
| Test questions | 25 |
| Intent classification accuracy | 100.0% |
| Expected scheme present in top 4 | 100.0% |
| Expected citation/no-citation behaviour | 100.0% |
| Required clarification triggered | 100.0% |
| Average local response time | 32.24 ms |

The dataset contains ten scheme searches, five eligibility questions, five Hindi/Hinglish questions, three unsupported requests and two missing-information questions. The exact cases are in `evaluation/golden_dataset.json` and can be rerun with:

```bash
python scripts/evaluate.py
```

## Critical interpretation

These numbers are **not a claim of 100% real-world JanScope accuracy**. The 25 questions are a small, curated regression/smoke dataset covering the eight included sample scheme records. They prove that the current code behaves as expected on known cases; they do not measure every scheme, language variation, ambiguous profile, changed rule or adversarial query.

In particular:

- Scheme retrieval success means the expected scheme appeared anywhere in the top four, not always rank one.
- Citation behaviour checks presence or absence, not whether every generated sentence is perfectly entailed.
- Gemini output was not evaluated because the run intentionally used no-key demo mode.
- The dataset is too small for statistical confidence or government decision-making.

## Next serious evaluation work

1. Expand to at least 200 independently written questions.
2. Separate retrieval precision/recall from generated-answer faithfulness.
3. Use multiple reviewers for relevance and citation entailment.
4. Test code-mixed language, spelling errors and all targeted states.
5. Add outdated, conflicting and malicious documents.
6. Measure Gemini-mode consistency over repeated runs.
7. Evaluate every encoded rule against official examples and edge cases.
8. Record top-1, top-3 and top-5 retrieval separately.
9. Track failures by scheme, intent and language rather than only an overall score.
