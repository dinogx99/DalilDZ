# Methodology

DalilDZ is an evidence and consistency engine, not a reputation engine.

## Order of operations

1. Preserve the submitted claim unchanged.
2. Normalize a separate comparison value.
3. Collect evidence with provenance.
4. Prefer deterministic rules.
5. Use similarity algorithms only where exact rules are inappropriate.
6. Keep ambiguous results reviewable.
7. Generate a historical report snapshot.

## Deterministic fields

RC, NIF, NIS and AI use exact comparison after punctuation/spacing/Arabic-digit normalization.

Legal forms are parsed independently from company names so an exact RC does not hide a SARL/EURL conflict.

Wilayas are normalized against the 58-wilaya list, including Arabic names and numeric codes.

## Names

Company-name matching removes common legal-form noise, normalizes accents/punctuation and uses token-set similarity. For Arabic/Latin comparisons an approximate Algerian-oriented transliteration is also evaluated. Similarity is explanatory evidence, not legal identity proof.

## Addresses

Addresses use normalized token similarity. They remain less deterministic than identifiers and can require manual review.

## Website evidence

A company-controlled website is self-published. It may show that submitted information is consistent with what the company publishes, but it is not equivalent to an official registry.

## Source health

A source that times out or blocks access is not evidence that a record does not exist. DalilDZ therefore keeps `SOURCE_UNAVAILABLE` distinct from `NOT_FOUND`.

## AI

AI can be used for difficult classification, extraction or explanation when configured. It is not used to override exact identifier, legal-form or other deterministic evidence.

## Reproducibility

Reports contain an input fingerprint derived from stable report inputs. Retrieval times and user-interface rendering are not used as a substitute for provenance.
