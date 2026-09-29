from datetime import datetime, timezone

from sqlalchemy.orm import Session as OrmSession

from app.core.domain import SourceHealth, Status, compare_claim, fingerprint, uid
from app.models.entities import (
    AnalysisJob,
    Case,
    Document,
    EvidenceRecord,
    ExtractedClaim,
    Report,
    SourceSnapshot,
    VerificationCheck,
)
from app.normalization.algeria import (
    normalize_address,
    normalize_company_name,
    normalize_domain,
    normalize_identifier,
    normalize_legal_form,
    normalize_phone,
    normalize_wilaya,
)
from app.services.reporting import build_report_payload
from app.sources.adapters import ADAPTERS


def _normalize_field(field: str, value: str | None) -> str | None:
    if value is None:
        return None
    if field in {"rc", "nif", "nis", "ai"}:
        return normalize_identifier(value)
    if field == "legal_form":
        return normalize_legal_form(value)
    if field == "wilaya":
        return normalize_wilaya(value)
    if field in {"website", "domain"}:
        return normalize_domain(value)
    if field in {"phone", "telephone"}:
        return normalize_phone(value)
    if field == "address":
        return normalize_address(value)
    if field in {"legal_name", "commercial_name"}:
        return normalize_company_name(value)
    return value.strip()


def _new_check(
    *,
    case_id: str,
    job_id: str,
    field: str,
    submitted: str | None,
    observed: str | None,
    evidence_record_id: str | None,
    status: Status,
    metadata: dict,
) -> VerificationCheck:
    return VerificationCheck(
        id=uid(),
        case_id=case_id,
        analysis_job_id=job_id,
        evidence_record_id=evidence_record_id,
        field=field,
        submitted_value=submitted,
        evidence_value=observed,
        status=status.value,
        method=metadata.get("method", "unspecified"),
        explanation=metadata.get("explanation", ""),
        metadata_json=metadata,
    )


async def analyze_case(db: OrmSession, case_id: str) -> tuple[AnalysisJob, Report]:
    case = db.get(Case, case_id)
    if not case:
        raise ValueError("CASE_NOT_FOUND")

    job = AnalysisJob(
        id=uid(),
        case_id=case_id,
        status="RUNNING",
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()

    try:
        documents = db.query(Document).filter(Document.case_id == case_id).all()
        extracted_claims = (
            db.query(ExtractedClaim)
            .filter(ExtractedClaim.case_id == case_id)
            .order_by(ExtractedClaim.created_at.asc())
            .all()
        )
        records: list[EvidenceRecord] = []
        checks: list[VerificationCheck] = []
        source_states: list[dict] = []

        for claim in extracted_claims:
            record = EvidenceRecord(
                id=uid(),
                case_id=case_id,
                analysis_job_id=job.id,
                source_id="uploaded_document",
                document_id=claim.document_id,
                field=claim.field,
                extracted_value=claim.original_value,
                normalized_value=claim.normalized_value or _normalize_field(
                    claim.field, claim.original_value
                ),
                extraction_method=claim.extraction_method,
                confidence=claim.confidence,
                status=Status.CONSISTENT.value,
                metadata_json={
                    "page": claim.page,
                    "location": claim.location,
                },
            )
            db.add(record)
            records.append(record)

        manual_records = (
            db.query(EvidenceRecord)
            .filter(
                EvidenceRecord.case_id == case_id,
                EvidenceRecord.analysis_job_id.is_(None),
                EvidenceRecord.source_id == "user_confirmed_official_source",
            )
            .order_by(EvidenceRecord.retrieved_at.asc())
            .all()
        )
        records.extend(manual_records)

        for adapter in ADAPTERS:
            health = await adapter.health_check()
            if health == SourceHealth.MANUAL_ONLY:
                source_states.append(adapter.metadata(health))
                continue

            result = await adapter.collect(case.claims or {})
            state = adapter.metadata(result.health)
            state["error_code"] = result.error_code
            source_states.append(state)

            if result.snapshot_hash:
                first_url = next(
                    (item.source_url for item in result.evidence if item.source_url),
                    None,
                )
                db.add(
                    SourceSnapshot(
                        id=uid(),
                        case_id=case_id,
                        source_id=adapter.source_id,
                        url=first_url,
                        sha256=result.snapshot_hash,
                        content_type=result.snapshot_metadata.get("content_type"),
                        metadata_json=result.snapshot_metadata,
                    )
                )

            for item in result.evidence:
                record = EvidenceRecord(
                    id=uid(),
                    case_id=case_id,
                    analysis_job_id=job.id,
                    source_id=adapter.source_id,
                    field=item.field,
                    extracted_value=item.value,
                    normalized_value=_normalize_field(item.field, item.value),
                    source_url=item.source_url,
                    source_snapshot_hash=result.snapshot_hash,
                    extraction_method=item.method,
                    confidence=item.confidence,
                    status=Status.CONSISTENT.value,
                    metadata_json=item.metadata,
                )
                db.add(record)
                records.append(record)

        db.flush()

        evidence_fields: set[str] = set()
        for record in records:
            evidence_fields.add(record.field)
            submitted = (case.claims or {}).get(record.field)
            status, metadata = compare_claim(
                record.field,
                submitted,
                record.extracted_value,
            )
            check = _new_check(
                case_id=case_id,
                job_id=job.id,
                field=record.field,
                submitted=submitted,
                observed=record.extracted_value,
                evidence_record_id=record.id,
                status=status,
                metadata={
                    **metadata,
                    "source_id": record.source_id,
                    "source_url": record.source_url,
                },
            )
            db.add(check)
            checks.append(check)

        for field, submitted in (case.claims or {}).items():
            if field in evidence_fields:
                continue

            unavailable_sources = [
                state
                for state in source_states
                if field in state.get("supported_fields", [])
                and state.get("health") in {
                    SourceHealth.UNAVAILABLE.value,
                    SourceHealth.DEGRADED.value,
                }
            ]
            manual_sources = [
                state
                for state in source_states
                if field in state.get("supported_fields", [])
                and state.get("health") == SourceHealth.MANUAL_ONLY.value
            ]

            if unavailable_sources:
                status = Status.SOURCE_UNAVAILABLE
                metadata = {
                    "method": "source_availability",
                    "sources": [item["id"] for item in unavailable_sources],
                    "explanation": (
                        "An automated source that could support this field was unavailable. "
                        "This is not the same as NOT_FOUND."
                    ),
                }
            elif manual_sources:
                status = Status.MANUAL_REVIEW_REQUIRED
                metadata = {
                    "method": "manual_source_required",
                    "sources": [item["id"] for item in manual_sources],
                    "explanation": (
                        "A relevant source is manual-only. Use the manual evidence workflow "
                        "and retain the official-source provenance."
                    ),
                }
            else:
                status = Status.NOT_VERIFIABLE
                metadata = {
                    "method": "no_available_evidence",
                    "explanation": "No evidence was collected for this submitted field.",
                }

            check = _new_check(
                case_id=case_id,
                job_id=job.id,
                field=field,
                submitted=submitted,
                observed=None,
                evidence_record_id=None,
                status=status,
                metadata=metadata,
            )
            db.add(check)
            checks.append(check)

        job.status = "COMPLETED"
        job.finished_at = datetime.now(timezone.utc)
        db.flush()

        payload = build_report_payload(
            case=case,
            job=job,
            documents=documents,
            evidence=records,
            checks=checks,
            sources=source_states,
        )
        report = Report(
            id=uid(),
            case_id=case_id,
            analysis_job_id=job.id,
            version="1.0",
            format="json",
            fingerprint=payload["input_fingerprint"],
            payload=payload,
        )
        db.add(report)
        db.commit()
        return job, report
    except Exception as exc:
        db.rollback()
        with db.begin():
            failed = db.get(AnalysisJob, job.id)
            if failed:
                failed.status = "FAILED"
                failed.error_code = exc.__class__.__name__.upper()
                failed.error_message = str(exc)[:1000]
                failed.finished_at = datetime.now(timezone.utc)
        raise
