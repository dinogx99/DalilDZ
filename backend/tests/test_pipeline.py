import asyncio

from app.core.db import Session
from app.core.domain import SourceHealth, Status, uid
from app.models.entities import Case, EvidenceRecord, VerificationCheck
from app.services.pipeline import analyze_case
from app.sources.base import CollectionResult, EvidenceSourceAdapter


class DegradedNIFSource(EvidenceSourceAdapter):
    source_id = "degraded_nif"
    display_name = "Synthetic degraded NIF source"
    source_type = "TEST"
    supported_fields = ("nif",)

    async def health_check(self):
        return SourceHealth.AVAILABLE

    async def collect(self, claims):
        return CollectionResult(
            health=SourceHealth.DEGRADED,
            error_code="SOURCE_TIMEOUT",
        )


def test_source_unavailable_is_not_not_found(monkeypatch):
    monkeypatch.setattr("app.services.pipeline.ADAPTERS", [DegradedNIFSource()])
    with Session() as db:
        case = Case(id=uid(), name="SYNTHETIC TEST COMPANY", claims={"nif": "123456789012345"})
        db.add(case)
        db.commit()
        job, report = asyncio.run(analyze_case(db, case.id))
        checks = (
            db.query(VerificationCheck)
            .filter(VerificationCheck.analysis_job_id == job.id)
            .all()
        )
        assert len(checks) == 1
        assert checks[0].status == Status.SOURCE_UNAVAILABLE.value
        assert checks[0].status != Status.NOT_FOUND.value
        assert report.payload["summary"][Status.SOURCE_UNAVAILABLE.value] == 1


def test_manual_official_evidence_participates_in_future_analysis(monkeypatch):
    monkeypatch.setattr("app.services.pipeline.ADAPTERS", [])
    with Session() as db:
        case = Case(id=uid(), name="SYNTHETIC ALPHA", claims={"rc": "16B0123456"})
        db.add(case)
        evidence = EvidenceRecord(
            id=uid(),
            case_id=case.id,
            analysis_job_id=None,
            source_id="user_confirmed_official_source",
            field="rc",
            extracted_value="16 B 0123456",
            normalized_value="16B0123456",
            extraction_method="USER_CONFIRMED_FROM_OFFICIAL_SOURCE",
            status=Status.CONSISTENT.value,
            metadata_json={"source_name": "Synthetic manual fixture"},
        )
        db.add(evidence)
        db.commit()
        first_job, first_report = asyncio.run(analyze_case(db, case.id))
        second_job, second_report = asyncio.run(analyze_case(db, case.id))
        first = (
            db.query(VerificationCheck)
            .filter(
                VerificationCheck.analysis_job_id == first_job.id,
                VerificationCheck.field == "rc",
            )
            .one()
        )
        assert first.status == Status.VERIFIED.value
        assert first_report.fingerprint == second_report.fingerprint
        assert second_job.id != first_job.id
