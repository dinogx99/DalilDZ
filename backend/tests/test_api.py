import io

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app


def png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (50, 30), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def test_case_workflow_manual_evidence_analysis_and_exports(monkeypatch):
    monkeypatch.setattr("app.services.pipeline.ADAPTERS", [])
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/cases",
            json={
                "name": "SYNTHETIC ALPHA DISTRIBUTION",
                "claims": {
                    "legal_name": "SYNTHETIC ALPHA DISTRIBUTION",
                    "rc": "16B0123456",
                },
            },
        )
        assert created.status_code == 201
        assert created.headers["x-request-id"]
        case_id = created.json()["id"]

        manual = client.post(
            f"/api/v1/cases/{case_id}/manual-evidence",
            json={
                "field": "rc",
                "value": "16 B 0123456",
                "source_name": "SYNTHETIC OFFICIAL-SOURCE FIXTURE",
                "source_url": "https://example.invalid/manual-check",
            },
        )
        assert manual.status_code == 201
        assert manual.json()["status"] == "VERIFIED"

        analysis = client.post(f"/api/v1/cases/{case_id}/analyze")
        assert analysis.status_code == 200
        assert analysis.json()["status"] == "COMPLETED"

        report = client.get(f"/api/v1/cases/{case_id}/report")
        assert report.status_code == 200
        body = report.json()
        assert body["input_fingerprint"]
        assert body["summary"]["VERIFIED"] == 1
        assert "does not determine whether" in body["disclaimer"]

        html = client.get(f"/api/v1/cases/{case_id}/report.html")
        assert html.status_code == 200
        assert "DalilDZ evidence report" in html.text

        csv_export = client.get(f"/api/v1/cases/{case_id}/report.csv")
        assert csv_export.status_code == 200
        assert "submitted_value" in csv_export.text

        timeline = client.get(f"/api/v1/cases/{case_id}/timeline")
        assert timeline.status_code == 200
        assert any(event["action"] == "analysis.completed" for event in timeline.json())


def test_upload_validates_image_content_and_marks_ocr_required():
    with TestClient(app) as client:
        case = client.post(
            "/api/v1/cases",
            json={"name": "SYNTHETIC IMAGE CASE", "claims": {}},
        ).json()
        response = client.post(
            f"/api/v1/cases/{case['id']}/documents",
            files={"file": ("invoice.png", png_bytes(), "image/png")},
        )
        assert response.status_code == 201
        assert response.json()["mime"] == "image/png"
        assert response.json()["ocr_required"] is True

        duplicate = client.post(
            f"/api/v1/cases/{case['id']}/documents",
            files={"file": ("renamed.png", png_bytes(), "image/png")},
        )
        assert duplicate.status_code == 409


def test_bulk_csv_import_and_case_listing():
    content = (
        "company_name,rc,nif,website,wilaya\n"
        "SYNTHETIC BETA,31B1111111,123456789012345,,Oran\n"
        "SYNTHETIC GAMMA,16B2222222,,,Alger\n"
    ).encode()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/bulk/import",
            files={"file": ("vendors.csv", content, "text/csv")},
        )
        assert response.status_code == 201
        assert response.json()["created"] == 2
        listed = client.get("/api/v1/cases")
        assert listed.status_code == 200
        assert listed.json()["total"] == 2


def test_source_metadata_distinguishes_manual_only():
    with TestClient(app) as client:
        response = client.get("/api/v1/sources")
        assert response.status_code == 200
        cnrc = next(item for item in response.json() if item["id"] == "cnrc_manual")
        assert cnrc["official"] is True
        assert cnrc["health"] == "MANUAL_ONLY"
        assert cnrc["automation_mode"] == "MANUAL_ONLY"


def test_entity_resolution_endpoint():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/entity-resolution",
            json={
                "submitted": {"legal_name": "SARL ALPHA", "rc": "16B0123456"},
                "observed": {"legal_name": "ALPHA S.A.R.L", "rc": "16 B 0123456"},
            },
        )
        assert response.status_code == 200
        assert response.json()["relation"] == "LIKELY_SAME_ENTITY"
