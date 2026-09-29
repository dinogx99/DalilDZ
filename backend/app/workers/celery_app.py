import asyncio

from celery import Celery

from app.core.config import settings
from app.core.db import Session
from app.services.pipeline import analyze_case


celery = Celery(
    "dalildz",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    timezone="UTC",
)


@celery.task(name="dalildz.analyze_case")
def analyze_case_task(case_id: str) -> dict:
    with Session() as db:
        job, report = asyncio.run(analyze_case(db, case_id))
        return {
            "case_id": case_id,
            "job_id": job.id,
            "report_id": report.id,
            "status": job.status,
            "fingerprint": report.fingerprint,
        }
