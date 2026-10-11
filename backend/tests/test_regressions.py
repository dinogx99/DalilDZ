"""Regression tests for bugs fixed after the initial baseline."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core.db import Session
from app.core.domain import SourceHealth, Status, uid
from app.main import app
from app.models.entities import AnalysisJob, Case, VerificationCheck
from app.services import web_intelligence
from app.services.pipeline import analyze_case
from app.sources.adapters import WebsitePublicSource
from app.sources.base import EvidenceSourceAdapter


class ExplodingWebsiteSource(EvidenceSourceAdapter):
    source_id = "exploding"
    display_name = "Synthetic exploding source"
    source_type = "TEST"
    supported_fields = ("website",)

    async def health_check(self):
        return SourceHealth.AVAILABLE

    async def collect(self, claims):
        raise RuntimeError("unexpected adapter bug")


def test_network_errors_become_source_fetch_errors(monkeypatch):
    # httpx errors are not OSError subclasses; they must not escape as raw exceptions.
    monkeypatch.setattr(web_intelligence, "validate_public_url", lambda url: url)
    with pytest.raises(web_intelligence.SourceFetchError, match="NETWORK_"):
        asyncio.run(web_intelligence.fetch_public_url("http://127.0.0.1:9/", respect_robots=False))


def test_adapter_crash_is_reported_as_source_unavailable(monkeypatch):
    monkeypatch.setattr("app.services.pipeline.ADAPTERS", [ExplodingWebsiteSource()])
    with Session() as db:
        case = Case(id=uid(), name="SYNTHETIC CRASH", claims={"website": "alpha.dz"})
        db.add(case)
        db.commit()
        job, report = asyncio.run(analyze_case(db, case.id))
        assert job.status == "COMPLETED"
        check = db.query(VerificationCheck).filter(VerificationCheck.analysis_job_id == job.id).one()
        assert check.status == Status.SOURCE_UNAVAILABLE.value
        assert report.payload["sources"][0]["error_code"] == "ADAPTER_ERROR:RuntimeError"


def test_website_without_scheme_is_fetched_over_https(monkeypatch):
    seen: list[str] = []

    async def fake_collect(url: str) -> dict:
        seen.append(url)
        return {"evidence": [], "snapshot_hash": "0" * 64, "snapshot_metadata": {}}

    monkeypatch.setattr("app.sources.adapters.collect_website_metadata", fake_collect)
    result = asyncio.run(WebsitePublicSource().collect({"website": "alpha.dz"}))
    assert seen == ["https://alpha.dz"]
    assert result.health == SourceHealth.AVAILABLE


def test_manual_check_is_not_duplicated_after_analysis(monkeypatch):
    monkeypatch.setattr("app.services.pipeline.ADAPTERS", [])
    with TestClient(app) as client:
        case_id = client.post(
            "/api/v1/cases", json={"name": "SYNTHETIC DEDUPE", "claims": {"rc": "16B0123456"}}
        ).json()["id"]
        client.post(
            f"/api/v1/cases/{case_id}/manual-evidence",
            json={"field": "rc", "value": "16B0123456", "source_name": "SYNTHETIC SOURCE"},
        )
        before = client.get(f"/api/v1/cases/{case_id}/checks").json()
        assert [item["field"] for item in before] == ["rc"]

        client.post(f"/api/v1/cases/{case_id}/analyze")
        after = client.get(f"/api/v1/cases/{case_id}/checks").json()
        assert [item["field"] for item in after] == ["rc"]
        assert after[0]["job_id"] is not None

        # Manual evidence recorded after the latest analysis is still visible.
        client.post(
            f"/api/v1/cases/{case_id}/manual-evidence",
            json={"field": "wilaya", "value": "Oran", "source_name": "SYNTHETIC SOURCE"},
        )
        latest = client.get(f"/api/v1/cases/{case_id}/checks").json()
        assert sorted(item["field"] for item in latest) == ["rc", "wilaya"]


def test_swagger_docs_csp_allows_its_assets():
    with TestClient(app) as client:
        response = client.get("/docs")
        assert response.status_code == 200
        assert "cdn.jsdelivr.net" in response.headers["content-security-policy"]
        api = client.get("/api/v1/health")
        assert "cdn.jsdelivr.net" not in api.headers["content-security-policy"]


def test_printable_report_allows_inline_styles(monkeypatch):
    monkeypatch.setattr("app.services.pipeline.ADAPTERS", [])
    with TestClient(app) as client:
        case_id = client.post(
            "/api/v1/cases", json={"name": "SYNTHETIC <b>HTML</b>", "claims": {"rc": "16B1"}}
        ).json()["id"]
        client.post(f"/api/v1/cases/{case_id}/analyze")
        response = client.get(f"/api/v1/cases/{case_id}/report.html")
        assert "style-src 'unsafe-inline'" in response.headers["content-security-policy"]
        assert "<b>HTML</b>" not in response.text
        assert "SYNTHETIC &lt;b&gt;HTML&lt;/b&gt;" in response.text


def test_queue_endpoint_reports_unavailable_broker(monkeypatch):
    def broken_delay(*_args, **_kwargs):
        raise ConnectionError("broker down")

    monkeypatch.setattr("app.api.routes.analyze_case_task.delay", broken_delay)
    with TestClient(app) as client:
        case_id = client.post("/api/v1/cases", json={"name": "SYNTHETIC QUEUE"}).json()["id"]
        response = client.post(f"/api/v1/cases/{case_id}/analyze/background")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "QUEUE_UNAVAILABLE"


def test_failed_jobs_are_recorded(monkeypatch):
    def explode(**_kwargs):
        raise ValueError("synthetic report failure")

    monkeypatch.setattr("app.services.pipeline.ADAPTERS", [])
    monkeypatch.setattr("app.services.pipeline.build_report_payload", explode)
    with Session() as db:
        case = Case(id=uid(), name="SYNTHETIC FAIL", claims={})
        db.add(case)
        db.commit()
        with pytest.raises(ValueError):
            asyncio.run(analyze_case(db, case.id))
        job = db.query(AnalysisJob).filter(AnalysisJob.case_id == case.id).one()
        assert job.status == "FAILED"
        assert job.error_code == "VALUEERROR"
