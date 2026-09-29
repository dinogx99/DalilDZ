# Data Sources

This document distinguishes real automation from manual, experimental and planned integrations.

| Adapter | Official | Automation | State | Primary role |
| --- | ---: | --- | --- | --- |
| Uploaded documents | user-supplied | local | IMPLEMENTED | identity/contact/document evidence |
| Submitted company website | no | automated public | IMPLEMENTED | self-published consistency evidence |
| DNS / TLS / RDAP | no | automated public | IMPLEMENTED | technical domain observations |
| CNRC / Sidjilcom | yes | manual | MANUAL_ONLY | legal/registry verification |
| PaddleOCR | local | optional | EXPERIMENTAL | text recovery for scanned documents |
| LLM provider | configured by operator | optional | IMPLEMENTED ABSTRACTION | interpretation only |

## CNRC / Sidjilcom

DalilDZ does not claim access to an undocumented government API. It does not bypass CAPTCHA, authentication, subscriptions or technical controls.

The manual evidence endpoint exists specifically so a reviewer can:
1. open the official source themselves;
2. confirm a field;
3. store the confirmed value;
4. retain source name/URL and method `USER_CONFIRMED_FROM_OFFICIAL_SOURCE`.

## Website collection

Website collection is intentionally bounded. It validates targets against SSRF rules, checks robots, limits redirects, enforces a response-size ceiling and does not crawl an entire domain.

## Domain intelligence

DNS, TLS and RDAP observations are technical metadata. They must never be interpreted as proof that a business is legitimate, solvent or safe.

## Adding sources

See [ADDING_A_SOURCE.md](ADDING_A_SOURCE.md). New adapters must document access conditions and failure semantics before automation is merged.
