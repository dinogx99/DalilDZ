from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(240), index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    claims: Mapped[dict] = mapped_column(JSON, default=dict)
    state: Mapped[str] = mapped_column(String(32), default="OPEN", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, onupdate=now_utc
    )


class BusinessEntity(Base):
    __tablename__ = "business_entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), index=True
    )
    legal_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    normalized_legal_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    arabic_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    latin_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    commercial_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    legal_form: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rc: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    nif: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    nis: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    ai: Mapped[str | None] = mapped_column(String(64), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    wilaya: Mapped[str | None] = mapped_column(String(100), nullable=True)
    commune: Mapped[str | None] = mapped_column(String(160), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    activities: Mapped[list] = mapped_column(JSON, default=list)
    activity_codes: Mapped[list] = mapped_column(JSON, default=list)
    website: Mapped[str | None] = mapped_column(Text, nullable=True)
    domains: Mapped[list] = mapped_column(JSON, default=list)
    emails: Mapped[list] = mapped_column(JSON, default=list)
    phones: Mapped[list] = mapped_column(JSON, default=list)
    representatives: Mapped[list] = mapped_column(JSON, default=list)
    source_references: Mapped[list] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    mime: Mapped[str] = mapped_column(String(80))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    text: Mapped[str] = mapped_column(Text, default="")
    document_type: Mapped[str] = mapped_column(String(64), default="unidentified")
    extraction_method: Mapped[str] = mapped_column(String(80), default="direct_text")
    ocr_required: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class ExtractedClaim(Base):
    __tablename__ = "extracted_claims"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(36), index=True)
    document_id: Mapped[str | None] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True
    )
    field: Mapped[str] = mapped_column(String(80), index=True)
    original_value: Mapped[str] = mapped_column(Text)
    normalized_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    location: Mapped[dict] = mapped_column(JSON, default=dict)
    extraction_method: Mapped[str] = mapped_column(String(80))
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class EvidenceSource(Base):
    __tablename__ = "evidence_sources"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(200))
    source_type: Mapped[str] = mapped_column(String(80))
    official: Mapped[bool] = mapped_column(Boolean, default=False)
    automation_mode: Mapped[str] = mapped_column(String(32), default="AUTOMATED")
    health: Mapped[str] = mapped_column(String(32), default="AVAILABLE")
    limitations: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_successful_access: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(36), index=True)
    source_id: Mapped[str] = mapped_column(String(80), index=True)
    document_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    field: Mapped[str] = mapped_column(String(80), index=True)
    extracted_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_snapshot_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extraction_method: Mapped[str] = mapped_column(String(80))
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="CONSISTENT", index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class VerificationCheck(Base):
    __tablename__ = "verification_checks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(36), index=True)
    analysis_job_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    evidence_record_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    field: Mapped[str] = mapped_column(String(80), index=True)
    submitted_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    method: Mapped[str] = mapped_column(String(100))
    explanation: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class SourceSnapshot(Base):
    __tablename__ = "source_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(36), index=True)
    source_id: Mapped[str] = mapped_column(String(80), index=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(36), index=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(36), index=True)
    analysis_job_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    version: Mapped[str] = mapped_column(String(32), default="1.0")
    format: Mapped[str] = mapped_column(String(20), default="json")
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    actor: Mapped[str] = mapped_column(String(80), default="api")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


Index("ix_evidence_case_field", EvidenceRecord.case_id, EvidenceRecord.field)
Index("ix_checks_case_field_status", VerificationCheck.case_id, VerificationCheck.field, VerificationCheck.status)
