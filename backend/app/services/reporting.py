import csv
import io
from collections import Counter
from datetime import UTC, datetime
from html import escape

from app.core.domain import fingerprint
from app.models.entities import AnalysisJob, Case, Document, EvidenceRecord, VerificationCheck

DISCLAIMER = (
    "DalilDZ does not determine whether an entity is trustworthy, solvent, legitimate, "
    "fraudulent, or safe. It reports evidence and inconsistencies found in supplied and "
    "publicly available information."
)


def build_report_payload(
    case: Case,
    job: AnalysisJob,
    documents: list[Document],
    evidence: list[EvidenceRecord],
    checks: list[VerificationCheck],
    sources: list[dict],
) -> dict:
    counts = Counter(check.status for check in checks)
    input_basis = {
        "case": {
            "id": case.id,
            "name": case.name,
            "claims": case.claims,
        },
        "documents": sorted(doc.sha256 for doc in documents),
        "evidence": sorted(
            [
            {
                "source_id": item.source_id,
                "field": item.field,
                "value": item.extracted_value,
                "snapshot": item.source_snapshot_hash,
            }
            for item in evidence
            ],
            key=lambda item: (
                item["source_id"],
                item["field"],
                item.get("value") or "",
                item.get("snapshot") or "",
            ),
        ),
        "checks": sorted(
            [
            {
                "field": check.field,
                "submitted": check.submitted_value,
                "observed": check.evidence_value,
                "status": check.status,
                "method": check.method,
            }
            for check in checks
            ],
            key=lambda item: (
                item["field"],
                item.get("submitted") or "",
                item.get("observed") or "",
                item["status"],
                item["method"],
            ),
        ),
    }
    report_fingerprint = fingerprint(input_basis)
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "input_fingerprint": report_fingerprint,
        "case": {
            "id": case.id,
            "name": case.name,
            "notes": case.notes,
            "submitted_claims": case.claims,
        },
        "analysis": {
            "job_id": job.id,
            "status": job.status,
        },
        "summary": dict(sorted(counts.items())),
        "findings": [
            {
                "id": check.id,
                "field": check.field,
                "submitted_value": check.submitted_value,
                "observed_value": check.evidence_value,
                "status": check.status,
                "method": check.method,
                "explanation": check.explanation,
                "evidence_record_id": check.evidence_record_id,
                "checked_at": check.checked_at.isoformat() if check.checked_at else None,
                "metadata": check.metadata_json,
            }
            for check in checks
        ],
        "documents": [
            {
                "id": doc.id,
                "filename": doc.filename,
                "mime": doc.mime,
                "sha256": doc.sha256,
                "document_type": doc.document_type,
                "extraction_method": doc.extraction_method,
                "ocr_required": doc.ocr_required,
            }
            for doc in documents
        ],
        "sources": sources,
        "methodology": {
            "identifiers": "Exact comparison after deterministic normalization.",
            "legal_forms": "Deterministic Algerian legal-form normalization.",
            "names": "Normalized token-set similarity; ambiguous matches require review.",
            "websites": "Public metadata with SSRF, redirect, timeout and size controls.",
            "precedence": "Deterministic evidence is not overridden by AI interpretation.",
        },
        "limitations": [
            "CNRC/Sidjilcom is manual-only unless a lawful documented automated interface is added.",
            "A company-controlled website is self-published evidence, not an official registry.",
            "DNS, TLS and RDAP metadata do not prove business legitimacy.",
            "Missing evidence is not equivalent to proof that a claim is false.",
        ],
        "disclaimer": DISCLAIMER,
    }


STATUS_COLORS = {
    "VERIFIED": ("#dcefe5", "#14543b"),
    "CONSISTENT": ("#e2f0ee", "#175c56"),
    "CONFLICTING": ("#f8dfdb", "#8a2e27"),
    "SOURCE_UNAVAILABLE": ("#f2e4cf", "#85501e"),
    "OUTDATED": ("#eee4d5", "#79571c"),
    "MANUAL_REVIEW_REQUIRED": ("#fff0c9", "#765714"),
}


def _badge(status: str) -> str:
    background, color = STATUS_COLORS.get(status, ("#ecebe6", "#5e625f"))
    return (
        f'<span class="badge" style="background:{background};color:{color}">'
        f"{escape(status.replace('_', ' '))}</span>"
    )


def _text(value: object) -> str:
    return escape(str(value)) if value not in (None, "") else "—"


def render_report_html(payload: dict) -> str:
    case = payload.get("case", {})
    findings = payload.get("findings", [])
    finding_rows = "".join(
        "<tr>"
        f"<td><code>{_text(item.get('field'))}</code></td>"
        f"<td>{_text(item.get('submitted_value'))}</td>"
        f"<td>{_text(item.get('observed_value'))}</td>"
        f"<td>{_badge(str(item.get('status', '')))}</td>"
        f"<td>{_text((item.get('metadata') or {}).get('source_id'))}</td>"
        f"<td>{_text(item.get('explanation'))}<br><small>{_text(item.get('method'))}</small></td>"
        "</tr>"
        for item in findings
    )
    summary_cards = "".join(
        f'<div class="card">{_badge(status)}<strong>{count}</strong></div>'
        for status, count in (payload.get("summary") or {}).items()
    ) or '<div class="card">No findings<strong>0</strong></div>'
    claim_rows = "".join(
        f"<tr><th>{_text(field)}</th><td>{_text(value)}</td></tr>"
        for field, value in (case.get("submitted_claims") or {}).items()
    ) or '<tr><td colspan="2">No submitted claims.</td></tr>'
    source_rows = "".join(
        "<tr>"
        f"<td>{_text(item.get('name'))}</td>"
        f"<td>{_text(item.get('automation_mode'))}</td>"
        f"<td>{_text(item.get('health'))}</td>"
        f"<td>{_text(item.get('error_code'))}</td>"
        f"<td>{_text(item.get('limitations'))}</td>"
        "</tr>"
        for item in payload.get("sources", [])
    ) or '<tr><td colspan="5">No automated sources were consulted.</td></tr>'
    document_rows = "".join(
        "<tr>"
        f"<td>{_text(item.get('filename'))}</td>"
        f"<td>{_text(item.get('document_type'))}</td>"
        f"<td>{_text(item.get('extraction_method'))}</td>"
        f"<td><code>{_text(item.get('sha256'))}</code></td>"
        "</tr>"
        for item in payload.get("documents", [])
    ) or '<tr><td colspan="4">No documents were attached.</td></tr>'
    limitations = "".join(f"<li>{_text(item)}</li>" for item in payload.get("limitations", []))
    methodology = "".join(
        f"<li><strong>{_text(key)}</strong>: {_text(value)}</li>"
        for key, value in (payload.get("methodology") or {}).items()
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DalilDZ evidence report — {_text(case.get('name'))}</title>
<style>
body{{font-family:Inter,"Segoe UI",Arial,sans-serif;max-width:1100px;margin:32px auto;padding:0 24px;color:#17202a;line-height:1.45}}
header{{display:flex;justify-content:space-between;align-items:flex-start;gap:20px;border-bottom:3px solid #0d625b;padding-bottom:16px}}
.brand{{font-weight:800;font-size:1.4rem;letter-spacing:-.03em}}.brand span{{color:#a96326}}
h1{{margin:6px 0 4px;color:#173f3b;font-size:1.9rem}}h2{{color:#173f3b;margin-top:34px;font-size:1.2rem}}
.meta{{color:#5e625f;font-size:.85rem}}code{{font-size:.82em;word-break:break-all}}
table{{width:100%;border-collapse:collapse;margin:12px 0;font-size:.88rem}}
th,td{{border:1px solid #d8d8d0;padding:8px 10px;text-align:left;vertical-align:top}}
thead th,.kv th{{background:#f4f1e8}}td:first-child{{white-space:nowrap}}.kv th{{width:200px}}small{{color:#66706d}}
.cards{{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0}}
.card{{border:1px solid #d8d3c7;border-radius:8px;padding:10px 14px;display:flex;align-items:center;gap:12px}}
.card strong{{font-size:1.4rem}}
.badge{{display:inline-block;padding:3px 8px;border-radius:999px;font:700 .68rem ui-monospace,monospace;white-space:nowrap}}
.note{{background:#fff8e8;padding:14px;border-left:4px solid #c77b30;margin-top:28px}}
button{{background:#0d625b;color:#fff;border:0;border-radius:6px;padding:9px 14px;font-weight:700;cursor:pointer}}
@media print{{body{{margin:0;max-width:none}}.no-print{{display:none}}h2{{break-after:avoid}}tr{{break-inside:avoid}}}}
</style>
</head>
<body>
<header>
<div>
<div class="brand">Dalil<span>DZ</span> evidence report</div>
<h1>{_text(case.get('name'))}</h1>
<div class="meta">Case <code>{_text(case.get('id'))}</code> · generated {_text(payload.get('generated_at'))}</div>
<div class="meta">Input fingerprint <code>{_text(payload.get('input_fingerprint'))}</code></div>
</div>
<button class="no-print" onclick="window.print()">Print / save as PDF</button>
</header>
<h2>Summary</h2>
<div class="cards">{summary_cards}</div>
<h2>Submitted claims</h2>
<table class="kv"><tbody>{claim_rows}</tbody></table>
<h2>Evidence findings</h2>
<table>
<thead><tr><th>Field</th><th>Submitted</th><th>Observed</th><th>Status</th><th>Source</th><th>Why / method</th></tr></thead>
<tbody>{finding_rows or '<tr><td colspan="6">No findings.</td></tr>'}</tbody>
</table>
<h2>Sources consulted</h2>
<table>
<thead><tr><th>Source</th><th>Mode</th><th>Health</th><th>Error</th><th>Limitations</th></tr></thead>
<tbody>{source_rows}</tbody>
</table>
<h2>Documents</h2>
<table>
<thead><tr><th>File</th><th>Type</th><th>Extraction</th><th>SHA-256</th></tr></thead>
<tbody>{document_rows}</tbody>
</table>
<h2>Methodology</h2>
<ul>{methodology}</ul>
<h2>Limitations</h2>
<ul>{limitations}</ul>
<div class="note">{_text(payload.get('disclaimer'))}</div>
</body></html>"""


def render_findings_csv(payload: dict) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "field",
            "submitted_value",
            "observed_value",
            "status",
            "method",
            "explanation",
            "evidence_record_id",
            "checked_at",
        ],
    )
    writer.writeheader()
    for finding in payload.get("findings", []):
        writer.writerow({key: finding.get(key) for key in writer.fieldnames})
    return output.getvalue()
