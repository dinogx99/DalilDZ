# Changelog

All notable changes are recorded here.

## [Unreleased]

### Fixed
- CI: frontend type check failed on Next.js `URLPattern` declarations; Ruff reported 29 errors under `make lint`.
- Security: upgraded Next.js 16.3.3 → 16.4.0 (critical advisories incl. GHSA-vcvr-r3jv-pc5j); `npm audit` is clean.
- Analysis crashed with HTTP 500 when a website timed out or refused the connection (httpx errors are not `OSError`); network failures are now `SOURCE_UNAVAILABLE`, and any adapter crash is isolated.
- Websites entered without a scheme (`alpha.dz`) were rejected instead of fetched over HTTPS.
- Documents were misclassified: every invoice with an `RC:` line became a registry extract, and "distribution" matched the `rib` marker.
- Manual official evidence appeared twice in the checks list after an analysis.
- The API Content-Security-Policy blocked Swagger UI (`/docs`) and removed all styling from the printable report.
- "Queue in background" blocked for ~20 s when Redis was down; it now fails fast with `QUEUE_UNAVAILABLE`, and the unused Celery result backend was removed.
- `/api/v1/health` returned a 500 instead of a 503 when the database was unreachable.
- Alembic failed on database URLs containing `%` (URL-encoded passwords).
- Web: uploads always showed an error after succeeding (`event.currentTarget` read after `await`).
- Web: the API URL was hard-coded to `http://backend:8000`, so `npm run dev` could not reach a local API; it is now `BACKEND_URL`.
- Web container now listens on `0.0.0.0`, installs from `package-lock.json` and has a health check.
- Mobile layout: status cards overflowed and the findings panel touched the screen edges.

### Added
- Case page: manual official-evidence form, add/update claim form, JSON export, background queue button, analysis history, source health, delete case.
- Home page: legal form / phone / email fields and a CSV/XLSX bulk-import card.
- Arabic / French / English across every page with a persisted language choice and RTL layout.
- Richer printable report: summary, submitted claims, sources, documents, methodology, limitations and a print/PDF button.
- Regression tests for each fix above; CI smoke test now exercises the full stack through the web proxy.
- provenance-oriented database model for cases, entities, extracted claims, evidence, checks, snapshots, jobs, reports and audit events;
- Algerian Arabic/French/Latin normalization including 58 wilayas;
- OCR provider abstraction and optional PaddleOCR integration;
- public website, DNS, TLS and RDAP evidence collection;
- immutable analysis/report history;
- manual official-source evidence workflow;
- CSV/XLSX bulk imports;
- expanded REST API, CLI, MCP server and Celery worker;
- trilingual case workflow UI;
- substantive test/evaluation suite and security workflows.

### Security
- SSRF/private-network checks, redirect validation and bounded fetching;
- non-root containers;
- dependency auditing and Dependabot.

## [1.0.0] - 2026-09-29

Initial public repository baseline.
