# Security Policy

DalilDZ processes untrusted files and URLs. Security bugs in ingestion, SSRF defenses, dependency handling or secret management are high priority.

## Implemented controls

- magic-byte MIME checks;
- bounded uploads;
- SHA-256 fingerprints;
- safe display filenames;
- ORM/parameterized database access;
- environment-only secrets;
- SSRF filtering for private, loopback, link-local and metadata targets;
- URL userinfo/unsafe-port rejection;
- redirect re-validation;
- HTTP timeout and response-size caps;
- robots-aware website fetching;
- request IDs and security headers;
- rate limiting;
- non-root application containers;
- CodeQL, dependency audits and Dependabot.

## Important residual risks

DNS answers can change between validation and connection (DNS rebinding/TOCTOU). Python HTTP clients do not currently expose a simple first-class way for this implementation to pin the validated IP while retaining normal TLS hostname validation. Deploy sensitive installations with egress/network controls in addition to application-level SSRF checks.

PDF/image parsers and optional OCR engines are complex native dependencies. Keep containers patched and avoid processing untrusted files with excessive privileges.

v1.0 has no built-in user authentication. Put deployments handling private business documents behind an access-control layer.

## Reporting a vulnerability

Do not open a public issue containing exploit details, credentials, private documents or sensitive targets. Contact the repository maintainer privately through an appropriate GitHub security channel when available.

Do not include real third-party commercial documents in a proof of concept unless you have permission.
