import argparse
import asyncio
import json
from pathlib import Path

from app.core.config import settings
from app.core.db import Session, init_db
from app.entity_resolution.resolver import resolve_entities
from app.extraction.ocr import get_ocr_provider
from app.models.entities import Report
from app.services.documents import process_document
from app.sources.adapters import ADAPTERS


def _json(value) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def cmd_doctor(_args) -> None:
    init_db()
    _json(
        {
            "dalildz": "1.0.0",
            "database": settings.database_url.split(":", 1)[0],
            "ocr_provider": settings.ocr_provider,
            "status": "ok",
        }
    )


def cmd_verify(args) -> None:
    submitted = {"legal_name": args.name, "rc": args.rc}
    observed = {"legal_name": args.observed_name, "rc": args.observed_rc}
    _json(resolve_entities(
        {k: v for k, v in submitted.items() if v},
        {k: v for k, v in observed.items() if v},
    ))


def cmd_document(args) -> None:
    data = Path(args.path).read_bytes()
    result = process_document(data, get_ocr_provider(settings.ocr_provider))
    _json(
        {
            "mime": result.mime,
            "sha256": result.digest,
            "document_type": result.document_type,
            "extraction_method": result.extraction_method,
            "ocr_required": result.ocr_required,
            "claims": [claim.__dict__ for claim in result.claims],
        }
    )


async def _source_status() -> list[dict]:
    output = []
    for adapter in ADAPTERS:
        health = await adapter.health_check()
        output.append(adapter.metadata(health))
    return output


def cmd_sources(_args) -> None:
    _json(asyncio.run(_source_status()))


def cmd_report(args) -> None:
    init_db()
    with Session() as db:
        report = (
            db.query(Report)
            .filter(Report.case_id == args.case_id)
            .order_by(Report.created_at.desc())
            .first()
        )
        _json(report.payload if report else {"error": "REPORT_NOT_FOUND"})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dalildz")
    commands = parser.add_subparsers(dest="command", required=True)

    doctor = commands.add_parser("doctor", help="Check local DalilDZ configuration")
    doctor.set_defaults(func=cmd_doctor)

    verify = commands.add_parser("verify", help="Compare two business identity descriptions")
    verify.add_argument("--name", required=True)
    verify.add_argument("--rc")
    verify.add_argument("--observed-name", required=True)
    verify.add_argument("--observed-rc")
    verify.set_defaults(func=cmd_verify)

    document = commands.add_parser("document", help="Parse a business document")
    document.add_argument("path")
    document.set_defaults(func=cmd_document)

    sources = commands.add_parser("sources", help="Show evidence-source health")
    sources.set_defaults(func=cmd_sources)

    report = commands.add_parser("report", help="Print latest report JSON")
    report.add_argument("case_id")
    report.set_defaults(func=cmd_report)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
