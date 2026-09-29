# Changelog

All notable changes are recorded here.

## [Unreleased]

### Added
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
