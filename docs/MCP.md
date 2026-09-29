# MCP Server

DalilDZ includes an MCP server built on the official Python MCP SDK.

## Start

```bash
python -m pip install -e backend
dalildz-mcp
```

The default transport is stdio.

## Tools

| Tool | Purpose |
| --- | --- |
| `compare_business_claims` | deterministic field comparison |
| `resolve_algerian_entity` | explainable entity resolution |
| `create_verification_case` | create a persistent case |
| `parse_business_document` | parse a base64 PDF/image |
| `get_case_evidence` | retrieve provenance-bearing evidence |
| `generate_evidence_report` | return the latest report |
| `check_source_status` | source health/limitations |

MCP clients should not reinterpret DalilDZ results as a trust score.
