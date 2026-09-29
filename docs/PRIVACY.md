# Privacy Architecture

Commercial invoices, quotations, RIB-related documents and supplier files can contain sensitive information. DalilDZ therefore defaults to local processing.

## Defaults

- no telemetry;
- no external AI provider;
- no automatic transmission of document bodies to third parties;
- request logs contain path/status/timing, not uploaded document contents;
- credentials are environment variables;
- file identity is tracked by SHA-256 and UUID-backed records.

## Optional AI

Setting `AI_PROVIDER` to an external provider changes the privacy boundary. Operators are responsible for the provider's data terms, retention policy and applicable contractual/legal requirements.

Local Ollama-compatible operation can keep model inference inside the operator's environment.

## Retention

DalilDZ exposes case deletion. Deployments should define their own retention period for PostgreSQL backups, logs and infrastructure snapshots. Deleting a live database record does not automatically erase an operator's external backups.

## Logging

Do not add document text, API keys, bank data or personal identifiers to application logs. New logging should use event names and opaque IDs.

## Multi-user deployments

v1.0 does not include authentication/tenant isolation. Do not expose a sensitive deployment directly to the public Internet without an appropriate identity/access layer.
