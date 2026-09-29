from collections import Counter
import csv
from datetime import datetime, timezone
from html import escape
import io

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
        "documents": [{"id": doc.id, "sha256": doc.sha256} for doc in documents],
        "evidence": [
            {
                "id": item.id,
                "source_id": item.source_id,
                "field": item.field,
                "value": item.extracted_value,
                "snapshot": item.source_snapshot_hash,
            }
            for item in evidence
        ],
        "checks": [
            {
                "field": check.field,
                "submitted": check.submitted_value,
                "observed": check.evidence_value,
                "status": check.status,
                "method": check.method,
            }
            for check in checks
        ],
    }
    report_fingerprint = fingerprint(input_basis)
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
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


def render_report_html(payload: dict) -> str:
    rows = []
    for finding in payload.get("findings", []):
        rows.append(
            "<tr>"
            f"<td>{escape(str(finding.get('field', '')))}</td>"
            f"<td>{escape(str(finding.get('submitted_value') or '—'))}</td>"
            f"<td>{escape(str(finding.get('observed_value') or '—'))}</td>"
            f"<td><strong>{escape(str(finding.get('status', '')))}</strong></td>"
            f"<td>{escape(str(finding.get('explanation', '')))}</td>"
            "</tr>"
        )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>DalilDZ report — {escape(payload['case']['name'])}</title>
<style>
body{{font-family:Arial,sans-serif;max-width:1100px;margin:40px auto;padding:0 24px;color:#17202a}}
h1,h2{{color:#173f3b}}table{{width:100%;border-collapse:collapse;margin:20px 0}}
th,td{{border:1px solid #d8d8d0;padding:10px;text-align:left;vertical-align:top}}
th{{background:#f4f1e8}}code{{font-size:.9em}}.note{{background:#fff8e8;padding:14px;border-left:4px solid #c77b30}}
@media print{{body{{margin:0;max-width:none}}}}
</style>
</head>
<body>
<h1>DalilDZ evidence report</h1>
<p><strong>Case:</strong> {escape(payload['case']['name'])}</p>
<p><strong>Input fingerprint:</strong> <code>{escape(payload['input_fingerprint'])}</code></p>
<h2>Evidence findings</h2>
<table>
<thead><tr><th>Field</th><th>Submitted</th><th>Observed</th><th>Status</th><th>Why</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
<div class="note">{escape(payload['disclaimer'])}</div>
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
