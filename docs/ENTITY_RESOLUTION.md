# Entity Resolution

Entity resolution answers a narrow question: **could two identity descriptions refer to the same business entity?** It does not answer whether that entity is trustworthy.

## Signal precedence

1. conflicting exact identifiers;
2. matching exact identifiers;
3. normalized legal-form comparison;
4. normalized/transliterated company-name similarity;
5. other supporting address/contact evidence.

A conflicting RC is not “fixed” by a similar company name.

## Legal form

Legal form is deliberately evaluated separately. Example:

```text
Submitted: SARL ALPHA — RC 16B0123456
Observed:  EURL ALPHA — RC 16B0123456
```

The resolver may conclude `LIKELY_SAME_ENTITY` because the RC is exact while simultaneously emitting a **legal-form conflict**.

## Ambiguity

Results include:
- `LIKELY_SAME_ENTITY`
- `POSSIBLE_MATCH`
- `CONFLICTING_IDENTIFIERS`
- `INSUFFICIENT_EVIDENCE`

Ambiguous entities are not silently merged.

## Evaluation corpus

Synthetic cases live in `evals/entity_resolution/cases.jsonl`. Run:

```bash
python scripts/run_evals.py
```
