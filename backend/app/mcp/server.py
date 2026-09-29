import base64

from mcp.server import MCPServer

from app.core.config import settings
from app.core.db import Session, init_db
from app.core.domain import compare_claim, uid
from app.entity_resolution.resolver import resolve_entities
from app.extraction.ocr import get_ocr_provider
from app.models.entities import Case, EvidenceRecord, Report
from app.services.documents import process_document
from app.sources.adapters import ADAPTERS


mcp = MCPServer("DalilDZ")


@mcp.tool()
def compare_business_claims(field: str, submitted: str, observed: str) -> dict:
    """Compare one submitted business claim against one observed value."""
    status, metadata = compare_claim(field, submitted, observed)
    return {"field": field, "status": status.value, **metadata}


@mcp.tool()
def resolve_algerian_entity(submitted: dict[str, str], observed: dict[str, str]) -> dict:
    """Resolve whether two Algerian business identity descriptions may refer to the same entity."""
    return resolve_entities(submitted, observed)


@mcp.tool()
def create_verification_case(
    name: str,
    rc: str | None = None,
    nif: str | None = None,
    website: str | None = None,
    wilaya: str | None = None,
) -> dict:
    """Create a DalilDZ verification case without making a trust or fraud judgment."""
    init_db()
    claims = {
        key: value
        for key, value in {
            "legal_name": name,
            "rc": rc,
            "nif": nif,
            "website": website,
            "wilaya": wilaya,
        }.items()
        if value
    }
    with Session() as db:
        case = Case(id=uid(), name=name, claims=claims)
        db.add(case)
        db.commit()
        return {"case_id": case.id, "name": case.name, "claims": case.claims}


@mcp.tool()
def parse_business_document(filename: str, content_base64: str) -> dict:
    """Parse one PDF/image supplied as base64 and return evidence-bearing extracted claims."""
    data = base64.b64decode(content_base64, validate=True)
    provider = get_ocr_provider(settings.ocr_provider)
    result = process_document(data, provider)
    return {
        "filename": filename,
        "mime": result.mime,
        "sha256": result.digest,
        "document_type": result.document_type,
        "extraction_method": result.extraction_method,
        "ocr_required": result.ocr_required,
        "claims": [
            {
                "field": claim.field,
                "value": claim.value,
                "page": claim.page,
                "location": claim.location,
                "method": claim.method,
                "confidence": claim.confidence,
            }
            for claim in result.claims
        ],
    }


@mcp.tool()
def get_case_evidence(case_id: str) -> list[dict]:
    """Return stored evidence with provenance for a case."""
    init_db()
    with Session() as db:
        items = (
            db.query(EvidenceRecord)
            .filter(EvidenceRecord.case_id == case_id)
            .order_by(EvidenceRecord.retrieved_at.desc())
            .limit(500)
            .all()
        )
        return [
            {
                "id": item.id,
                "source_id": item.source_id,
                "field": item.field,
                "value": item.extracted_value,
                "method": item.extraction_method,
                "source_url": item.source_url,
                "snapshot_hash": item.source_snapshot_hash,
                "retrieved_at": item.retrieved_at.isoformat(),
            }
            for item in items
        ]


@mcp.tool()
def generate_evidence_report(case_id: str) -> dict:
    """Return the most recent immutable evidence report for a case."""
    init_db()
    with Session() as db:
        report = (
            db.query(Report)
            .filter(Report.case_id == case_id)
            .order_by(Report.created_at.desc())
            .first()
        )
        if not report:
            return {"error": "REPORT_NOT_FOUND", "case_id": case_id}
        return report.payload


@mcp.tool()
async def check_source_status() -> list[dict]:
    """Return source automation mode, limitations and current health."""
    output = []
    for adapter in ADAPTERS:
        health = await adapter.health_check()
        output.append(adapter.metadata(health))
    return output


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
