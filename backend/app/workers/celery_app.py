import asyncio

from celery import Celery

from app.core.config import settings
from app.core.db import Session
from app.services.pipeline import analyze_case

celery = Celery(
    "dalildz",
    broker=settings.redis_url,
    # Job state and reports are persisted in the database (AnalysisJob/Report), so no
    # Celery result backend is needed.
)
celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    # Fail fast when the broker is down so the API can answer QUEUE_UNAVAILABLE
    # instead of blocking the request while kombu retries forever.
    broker_connection_timeout=3,
    broker_connection_retry_on_startup=True,
    task_publish_retry_policy={"max_retries": 1, "interval_start": 0, "interval_step": 1},
    redis_socket_connect_timeout=3,
    task_ignore_result=True,
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
