from datetime import datetime, timezone

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy import desc

from app.core.config import settings
from app.core.db import Session
from app.core.domain import Status, compare_claim, uid
from app.entity_resolution.resolver import resolve_entities
from app.extraction.ocr import get_ocr_provider
from app.models.entities import (
    AnalysisJob,
    AuditEvent,
    BusinessEntity,
    Case,
    Document,
    EvidenceRecord,
    ExtractedClaim,
    Report,
    SourceSnapshot,
    VerificationCheck,
)
from app.normalization.algeria import (
    normalize_company_name,
    normalize_identifier,
    normalize_legal_form,
    normalize_wilaya,
)
from app.schemas import CaseCreate, CasePatch, ClaimCreate, EntityResolutionRequest, ManualEvidenceCreate
from app.services.audit import record_audit
from app.services.bulk import parse_bulk_file
from app.services.documents import process_document
from app.services.pipeline import analyze_case
from app.services.reporting import render_findings_csv, render_report_html
from app.services.security import sanitize_filename
from app.sources.adapters import ADAPTERS
from app.workers.celery_app import analyze_case_task


r = APIRouter(prefix="/api/v1")


def fail(status_code: int, code: str, message: str) -> None:
    raise HTTPException(status_code=status_code, detail={"code": code, "message": message})


def case_dict(case: Case) -> dict:
    return {
        "id": case.id,
        "name": case.name,
        "notes": case.notes,
        "claims": case.claims,
        "state": case.state,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
    }


def sync_entity(db, case: Case) -> BusinessEntity:
    entity = (
        db.query(BusinessEntity)
        .filter(BusinessEntity.case_id == case.id)
        .order_by(BusinessEntity.updated_at.desc())
        .first()
    )
    claims = case.claims or {}
    if not entity:
        entity = BusinessEntity(id=uid(), case_id=case.id)
        db.add(entity)
    entity.legal_name = claims.get("legal_name") or case.name
    entity.normalized_legal_name = normalize_company_name(entity.legal_name)
    entity.arabic_name = claims.get("arabic_name")
    entity.latin_name = claims.get("latin_name")
    entity.commercial_name = claims.get("commercial_name")
    entity.legal_form = normalize_legal_form(claims.get("legal_form"))
    entity.rc = normalize_identifier(claims.get("rc"))
    entity.nif = normalize_identifier(claims.get("nif"))
    entity.nis = normalize_identifier(claims.get("nis"))
    entity.ai = normalize_identifier(claims.get("ai"))
    entity.address = claims.get("address")
    entity.wilaya = normalize_wilaya(claims.get("wilaya"))
    entity.commune = claims.get("commune")
    entity.postal_code = claims.get("postal_code")
    entity.website = claims.get("website")
    entity.emails = [claims["email"]] if claims.get("email") else []
    entity.phones = [claims["phone"]] if claims.get("phone") else []
    entity.updated_at = datetime.now(timezone.utc)
    return entity


def latest_job(db, case_id: str) -> AnalysisJob | None:
    return (
        db.query(AnalysisJob)
        .filter(AnalysisJob.case_id == case_id)
        .order_by(desc(AnalysisJob.created_at))
        .first()
    )


def latest_report(db, case_id: str) -> Report | None:
    return (
        db.query(Report)
        .filter(Report.case_id == case_id)
        .order_by(desc(Report.created_at))
        .first()
    )


@r.get("/health")
def health():
    with Session() as db:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
    return {"status": "ok", "version": "1.0.0", "database": "ok"}


@r.get("/cases")
def list_cases(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    with Session() as db:
        cases = (
            db.query(Case)
            .order_by(desc(Case.updated_at))
            .offset(offset)
            .limit(limit)
            .all()
        )
        total = db.query(Case).count()
        return {"items": [case_dict(item) for item in cases], "total": total}


@r.post("/cases", status_code=201)
def create_case(payload: CaseCreate, request: Request):
    with Session() as db:
        case = Case(
            id=uid(),
            name=payload.name,
            notes=payload.notes,
            claims=dict(payload.claims),
        )
        db.add(case)
        db.flush()
        sync_entity(db, case)
        record_audit(
            db,
            "case.created",
            case_id=case.id,
            correlation_id=request.state.correlation_id,
            metadata={"claim_fields": sorted(case.claims)},
        )
        db.commit()
        return case_dict(case)


@r.get("/cases/{case_id}")
def get_case(case_id: str):
    with Session() as db:
        case = db.get(Case, case_id)
        if not case:
            fail(404, "CASE_NOT_FOUND", "Verification case does not exist.")
        return case_dict(case)


@r.patch("/cases/{case_id}")
def update_case(case_id: str, payload: CasePatch, request: Request):
    with Session() as db:
        case = db.get(Case, case_id)
        if not case:
            fail(404, "CASE_NOT_FOUND", "Verification case does not exist.")
        changed: list[str] = []
        if payload.name is not None:
            case.name = payload.name
            changed.append("name")
        if payload.notes is not None:
            case.notes = payload.notes
            changed.append("notes")
        if payload.claims is not None:
            case.claims = dict(payload.claims)
            changed.append("claims")
        sync_entity(db, case)
        record_audit(
            db,
            "case.updated",
            case_id=case.id,
            correlation_id=request.state.correlation_id,
            metadata={"changed": changed},
        )
        db.commit()
        return case_dict(case)


@r.post("/cases/{case_id}/claims", status_code=201)
def add_claim(case_id: str, payload: ClaimCreate, request: Request):
    with Session() as db:
        case = db.get(Case, case_id)
        if not case:
            fail(404, "CASE_NOT_FOUND", "Verification case does not exist.")
        claims = dict(case.claims or {})
        claims[payload.field] = payload.value
        case.claims = claims
        sync_entity(db, case)
        record_audit(
            db,
            "claim.submitted",
            case_id=case.id,
            correlation_id=request.state.correlation_id,
            metadata={"field": payload.field},
        )
        db.commit()
        return {"field": payload.field, "value": payload.value}


@r.delete("/cases/{case_id}", status_code=204)
def delete_case(case_id: str):
    with Session() as db:
        case = db.get(Case, case_id)
        if not case:
            return None
        for model in (
            AuditEvent,
            Report,
            VerificationCheck,
            EvidenceRecord,
            SourceSnapshot,
            ExtractedClaim,
            Document,
            BusinessEntity,
            AnalysisJob,
        ):
            db.query(model).filter(model.case_id == case_id).delete(synchronize_session=False)
        db.delete(case)
        db.commit()
    return None


@r.get("/cases/{case_id}/documents")
def list_documents(case_id: str):
    with Session() as db:
        docs = (
            db.query(Document)
            .filter(Document.case_id == case_id)
            .order_by(desc(Document.created_at))
            .all()
        )
        return [
            {
                "id": doc.id,
                "filename": doc.filename,
                "mime": doc.mime,
                "size_bytes": doc.size_bytes,
                "sha256": doc.sha256,
                "document_type": doc.document_type,
                "extraction_method": doc.extraction_method,
                "ocr_required": doc.ocr_required,
                "created_at": doc.created_at,
            }
            for doc in docs
        ]


@r.post("/cases/{case_id}/documents", status_code=201)
async def upload_document(case_id: str, request: Request, file: UploadFile = File(...)):
    data = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        fail(413, "FILE_TOO_LARGE", f"Maximum upload is {settings.max_upload_mb} MB.")

    try:
        provider = get_ocr_provider(settings.ocr_provider)
        processed = process_document(data, provider)
    except ValueError as exc:
        fail(400, str(exc), "The uploaded file could not be accepted.")
    except RuntimeError as exc:
        fail(503, "OCR_FAILED", str(exc))
    except Exception:
        fail(400, "INVALID_DOCUMENT", "The document could not be parsed safely.")

    with Session() as db:
        case = db.get(Case, case_id)
        if not case:
            fail(404, "CASE_NOT_FOUND", "Verification case does not exist.")

        duplicate = (
            db.query(Document)
            .filter(Document.case_id == case_id, Document.sha256 == processed.digest)
            .first()
        )
        if duplicate:
            fail(409, "DUPLICATE_DOCUMENT", "This exact document is already attached.")

        document = Document(
            id=uid(),
            case_id=case_id,
            filename=sanitize_filename(file.filename or "upload"),
            mime=processed.mime,
            size_bytes=len(data),
            sha256=processed.digest,
            text=processed.text,
            document_type=processed.document_type,
            extraction_method=processed.extraction_method,
            ocr_required=processed.ocr_required,
            metadata_json={"pages": processed.pages},
        )
        db.add(document)
        db.flush()

        extracted = []
        for item in processed.claims:
            claim = ExtractedClaim(
                id=uid(),
                case_id=case_id,
                document_id=document.id,
                field=item.field,
                original_value=item.value,
                normalized_value=None,
                page=item.page,
                location=item.location,
                extraction_method=item.method,
                confidence=item.confidence,
            )
            db.add(claim)
            extracted.append(
                {
                    "field": item.field,
                    "value": item.value,
                    "page": item.page,
                    "location": item.location,
                    "method": item.method,
                    "confidence": item.confidence,
                }
            )

        record_audit(
            db,
            "document.uploaded",
            case_id=case_id,
            correlation_id=request.state.correlation_id,
            metadata={
                "document_id": document.id,
                "sha256": document.sha256,
                "mime": document.mime,
                "claims_extracted": len(extracted),
            },
        )
        db.commit()
        return {
            "id": document.id,
            "filename": document.filename,
            "mime": document.mime,
            "sha256": document.sha256,
            "document_type": document.document_type,
            "extraction_method": document.extraction_method,
            "ocr_required": document.ocr_required,
            "claims": extracted,
        }


@r.post("/cases/{case_id}/manual-evidence", status_code=201)
def add_manual_evidence(case_id: str, payload: ManualEvidenceCreate, request: Request):
    with Session() as db:
        case = db.get(Case, case_id)
        if not case:
            fail(404, "CASE_NOT_FOUND", "Verification case does not exist.")

        status, metadata = compare_claim(
            payload.field,
            (case.claims or {}).get(payload.field),
            payload.value,
        )
        evidence = EvidenceRecord(
            id=uid(),
            case_id=case_id,
            analysis_job_id=None,
            source_id="user_confirmed_official_source",
            field=payload.field,
            extracted_value=payload.value,
            normalized_value=None,
            source_url=payload.source_url,
            extraction_method="USER_CONFIRMED_FROM_OFFICIAL_SOURCE",
            confidence=None,
            status=Status.CONSISTENT.value,
            metadata_json={
                "source_name": payload.source_name,
                "note": payload.note,
                "manual": True,
            },
        )
        db.add(evidence)
        db.flush()
        check = VerificationCheck(
            id=uid(),
            case_id=case_id,
            analysis_job_id=None,
            evidence_record_id=evidence.id,
            field=payload.field,
            submitted_value=(case.claims or {}).get(payload.field),
            evidence_value=payload.value,
            status=status.value,
            method=metadata["method"],
            explanation=metadata["explanation"],
            metadata_json={
                **metadata,
                "source_id": evidence.source_id,
                "source_name": payload.source_name,
                "source_url": payload.source_url,
            },
        )
        db.add(check)
        record_audit(
            db,
            "evidence.manual_added",
            case_id=case_id,
            correlation_id=request.state.correlation_id,
            metadata={"field": payload.field, "source_name": payload.source_name},
        )
        db.commit()
        return {
            "evidence_id": evidence.id,
            "check_id": check.id,
            "status": check.status,
            "explanation": check.explanation,
        }


@r.post("/cases/{case_id}/analyze")
async def run_analysis(case_id: str, request: Request):
    with Session() as db:
        if not db.get(Case, case_id):
            fail(404, "CASE_NOT_FOUND", "Verification case does not exist.")
        try:
            job, report = await analyze_case(db, case_id)
        except Exception as exc:
            fail(500, "ANALYSIS_FAILED", str(exc)[:500])
        record_audit(
            db,
            "analysis.completed",
            case_id=case_id,
            correlation_id=request.state.correlation_id,
            metadata={"job_id": job.id, "report_id": report.id},
        )
        db.commit()
        return {
            "job_id": job.id,
            "status": job.status,
            "report_id": report.id,
            "fingerprint": report.fingerprint,
        }


@r.post("/cases/{case_id}/refresh")
async def refresh_evidence(case_id: str, request: Request):
    return await run_analysis(case_id, request)


@r.post("/cases/{case_id}/analyze/background", status_code=202)
def queue_analysis(case_id: str, request: Request):
    with Session() as db:
        if not db.get(Case, case_id):
            fail(404, "CASE_NOT_FOUND", "Verification case does not exist.")
        try:
            task = analyze_case_task.delay(case_id)
        except Exception:
            fail(503, "QUEUE_UNAVAILABLE", "Background analysis queue is unavailable.")
        record_audit(
            db,
            "analysis.queued",
            case_id=case_id,
            correlation_id=request.state.correlation_id,
            metadata={"celery_task_id": task.id},
        )
        db.commit()
        return {"task_id": task.id, "state": "QUEUED"}


@r.get("/cases/{case_id}/jobs")
def list_analysis_jobs(case_id: str):
    with Session() as db:
        if not db.get(Case, case_id):
            fail(404, "CASE_NOT_FOUND", "Verification case does not exist.")
        jobs = (
            db.query(AnalysisJob)
            .filter(AnalysisJob.case_id == case_id)
            .order_by(desc(AnalysisJob.created_at))
            .limit(100)
            .all()
        )
        return [
            {
                "id": job.id,
                "status": job.status,
                "error_code": job.error_code,
                "error_message": job.error_message,
                "created_at": job.created_at,
                "started_at": job.started_at,
                "finished_at": job.finished_at,
            }
            for job in jobs
        ]


@r.get("/cases/{case_id}/evidence")
def get_evidence(case_id: str, job_id: str | None = None):
    with Session() as db:
        selected_job = job_id or (latest_job(db, case_id).id if latest_job(db, case_id) else None)
        query = db.query(EvidenceRecord).filter(EvidenceRecord.case_id == case_id)
        if selected_job:
            query = query.filter(
                (EvidenceRecord.analysis_job_id == selected_job)
                | (EvidenceRecord.analysis_job_id.is_(None))
            )
        records = query.order_by(desc(EvidenceRecord.retrieved_at)).all()
        return [
            {
                "id": item.id,
                "job_id": item.analysis_job_id,
                "source_id": item.source_id,
                "field": item.field,
                "value": item.extracted_value,
                "normalized_value": item.normalized_value,
                "source_url": item.source_url,
                "snapshot_hash": item.source_snapshot_hash,
                "method": item.extraction_method,
                "confidence": item.confidence,
                "retrieved_at": item.retrieved_at,
                "metadata": item.metadata_json,
            }
            for item in records
        ]


@r.get("/cases/{case_id}/checks")
def get_checks(case_id: str, job_id: str | None = None):
    with Session() as db:
        selected_job = job_id or (latest_job(db, case_id).id if latest_job(db, case_id) else None)
        query = db.query(VerificationCheck).filter(VerificationCheck.case_id == case_id)
        if selected_job:
            query = query.filter(
                (VerificationCheck.analysis_job_id == selected_job)
                | (VerificationCheck.analysis_job_id.is_(None))
            )
        checks = query.order_by(desc(VerificationCheck.checked_at)).all()
        return [
            {
                "id": item.id,
                "job_id": item.analysis_job_id,
                "field": item.field,
                "submitted_value": item.submitted_value,
                "evidence_value": item.evidence_value,
                "status": item.status,
                "method": item.method,
                "explanation": item.explanation,
                "evidence_record_id": item.evidence_record_id,
                "checked_at": item.checked_at,
                "metadata": item.metadata_json,
            }
            for item in checks
        ]


@r.get("/cases/{case_id}/report")
def get_report(case_id: str):
    with Session() as db:
        report = latest_report(db, case_id)
        if not report:
            fail(404, "REPORT_NOT_FOUND", "Run analysis before requesting a report.")
        return report.payload


@r.get("/cases/{case_id}/report.html", response_class=HTMLResponse)
def get_report_html(case_id: str):
    with Session() as db:
        report = latest_report(db, case_id)
        if not report:
            fail(404, "REPORT_NOT_FOUND", "Run analysis before requesting a report.")
        return HTMLResponse(render_report_html(report.payload))


@r.get("/cases/{case_id}/report.csv", response_class=PlainTextResponse)
def get_report_csv(case_id: str):
    with Session() as db:
        report = latest_report(db, case_id)
        if not report:
            fail(404, "REPORT_NOT_FOUND", "Run analysis before requesting a report.")
        return PlainTextResponse(
            render_findings_csv(report.payload),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="dalildz-{case_id}.csv"'},
        )


@r.get("/cases/{case_id}/timeline")
def get_timeline(case_id: str):
    with Session() as db:
        events = (
            db.query(AuditEvent)
            .filter(AuditEvent.case_id == case_id)
            .order_by(desc(AuditEvent.created_at))
            .limit(500)
            .all()
        )
        return [
            {
                "id": event.id,
                "action": event.action,
                "actor": event.actor,
                "correlation_id": event.correlation_id,
                "metadata": event.metadata_json,
                "created_at": event.created_at,
            }
            for event in events
        ]


@r.post("/bulk/import", status_code=201)
async def bulk_import(request: Request, file: UploadFile = File(...)):
    data = await file.read(5 * 1024 * 1024 + 1)
    if len(data) > 5 * 1024 * 1024:
        fail(413, "FILE_TOO_LARGE", "Bulk import is limited to 5 MB.")
    try:
        rows = parse_bulk_file(data)
    except (ValueError, UnicodeDecodeError) as exc:
        fail(400, str(exc), "Bulk input must be CSV or XLSX with supported columns.")

    created = []
    with Session() as db:
        for row in rows:
            name = row.get("company_name")
            if not name:
                continue
            claims = {key: value for key, value in row.items() if key != "company_name" and value}
            claims["legal_name"] = name
            case = Case(id=uid(), name=name, claims=claims)
            db.add(case)
            db.flush()
            sync_entity(db, case)
            created.append(case.id)
        record_audit(
            db,
            "bulk.imported",
            correlation_id=request.state.correlation_id,
            metadata={"created_cases": len(created)},
        )
        db.commit()
    return {"created": len(created), "case_ids": created}


@r.post("/entity-resolution")
def entity_resolution(payload: EntityResolutionRequest):
    return resolve_entities(payload.submitted, payload.observed)


@r.get("/sources")
async def list_sources():
    output = []
    for adapter in ADAPTERS:
        health = await adapter.health_check()
        output.append(adapter.metadata(health))
    return output


@r.get("/sources/health")
async def source_health():
    return await list_sources()
