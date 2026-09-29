# Contributing to DalilDZ

Contributions should improve evidence quality, reproducibility or safe Algerian-source coverage.

## Setup

```bash
make setup
make test
make lint
```

## Pull requests

Keep PRs focused. Add tests for new normalization rules, verification rules, source adapters and security behavior.

A source PR must document:
- source owner/type;
- official vs public status;
- automation constraints;
- fields supported;
- source-health semantics;
- failure behavior;
- privacy/legal considerations.

## Test data

Use synthetic data unless redistribution rights are clear. Fictional Algerian businesses in fixtures must be visibly marked `SYNTHETIC TEST DATA`.

## Code principles

- deterministic rules before AI;
- no trust score;
- provenance before convenience;
- source unavailable is not not found;
- no secret keys in Git;
- no giant multi-purpose service modules when a smaller boundary is clearer.
