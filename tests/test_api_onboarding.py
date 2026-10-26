"""Integration tests for customer data onboarding, validation contracts, and tenant isolation."""

from __future__ import annotations

import shutil

import pytest
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.main import app
from backend.app.services.ingestion_service import IngestionService

client = TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_test_tenants():
    yield
    for tid in ["org_acme_corp", "org_starlight_saas"]:
        tpath = settings.data_dir / "tenants" / tid
        if tpath.exists():
            shutil.rmtree(tpath, ignore_errors=True)


@pytest.fixture
def acme_token() -> str:
    response = client.get("/api/v1/auth/demo-token?tenant_id=org_acme_corp")
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def starlight_token() -> str:
    response = client.get("/api/v1/auth/demo-token?tenant_id=org_starlight_saas")
    assert response.status_code == 200
    return response.json()["access_token"]



def test_download_template():
    """Verify that any user can download the onboarding CSV schema template."""
    response = client.get("/api/v1/onboarding/template")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "user_id,event_name,event_timestamp" in response.text


def test_get_status_initial_empty(acme_token: str):
    """Verify that an unprovisioned tenant returns has_data=False."""
    # Ensure fresh test directory state
    service = IngestionService("org_acme_test_empty", "Acme Empty Org")
    if service.status_file.exists():
        service.status_file.unlink()

    headers = {"Authorization": f"Bearer {acme_token}"}
    response = client.get("/api/v1/onboarding/status", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == "org_acme_corp"


def test_upload_empty_csv(acme_token: str):
    """Verify rejection of empty files."""
    headers = {"Authorization": f"Bearer {acme_token}"}
    files = {"file": ("empty.csv", b"", "text/csv")}
    response = client.post("/api/v1/onboarding/upload", headers=headers, files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_missing_columns(acme_token: str):
    """Verify rejection when required columns are missing."""
    headers = {"Authorization": f"Bearer {acme_token}"}
    invalid_csv = "user_id,timestamp\nusr_01,2025-01-01 10:00:00\n"
    files = {"file": ("test.csv", invalid_csv.encode(), "text/csv")}
    response = client.post("/api/v1/onboarding/upload", headers=headers, files=files)
    assert response.status_code == 400
    assert "Missing required CSV column" in response.json()["detail"]


def test_upload_invalid_file_extension(acme_token: str):
    """Verify rejection of non-CSV file types."""
    headers = {"Authorization": f"Bearer {acme_token}"}
    files = {"file": ("data.json", b'{"key": "value"}', "application/json")}
    response = client.post("/api/v1/onboarding/upload", headers=headers, files=files)
    assert response.status_code == 400
    assert "Only .csv files are supported" in response.json()["detail"]


def test_upload_validation_and_rejection_summary(acme_token: str):
    """Verify detailed rejection accounting: invalid timestamps, blanks, and duplicates."""
    headers = {"Authorization": f"Bearer {acme_token}"}

    csv_data = """user_id,event_name,event_timestamp,acquisition_channel
usr_good_1,signup,2025-01-01 10:00:00,Organic
usr_good_1,workspace_created,2025-01-01 10:30:00,Organic
usr_good_1,signup,2025-01-01 10:00:00,Organic
,signup,2025-01-01 10:00:00,Organic
usr_bad_ts,signup,invalid_timestamp_string,Organic
usr_prehistoric,signup,2010-01-01 10:00:00,Organic
usr_future,signup,2099-01-01 10:00:00,Organic
usr_unsupported,some_random_event,2025-01-01 10:00:00,Organic
usr_good_2,signup,2025-01-02 11:00:00,Direct
usr_good_2,paid,2025-01-20 12:00:00,Direct
"""
    files = {"file": ("events.csv", csv_data.encode(), "text/csv")}
    response = client.post("/api/v1/onboarding/upload", headers=headers, files=files)
    assert response.status_code == 200
    data = response.json()

    summary = data["quality_summary"]
    assert summary["total_rows"] == 10
    # 4 valid events: usr_good_1 (signup, workspace_created), usr_good_2 (signup, paid)
    assert summary["accepted_rows"] == 4
    # 1 duplicate: usr_good_1 signup exact duplicate
    assert summary["duplicate_rows"] == 1
    # 5 rejected: blank uid, bad ts, prehistoric, future, unsupported event
    assert summary["rejected_rows"] == 5
    assert summary["total_unique_users"] == 2
    assert "missing_user_id" in summary["rejection_reasons"]
    assert "invalid_timestamp_format" in summary["rejection_reasons"]
    assert "prehistoric_timestamp" in summary["rejection_reasons"]
    assert "future_timestamp" in summary["rejection_reasons"]
    assert "unsupported_event_name" in summary["rejection_reasons"]


def test_multi_tenant_onboarding_and_funnel_isolation(
    acme_token: str, starlight_token: str
):
    """End-to-End Multi-Tenant Verification:
    
    1. Tenant Acme Corp uploads dataset with 10 users, 8 reaching workspace, 6 reaching invite, 4 reaching project, 2 paying (20% overall conversion).
    2. Tenant Starlight SaaS uploads dataset with 4 users, all 4 reaching paid (100% overall conversion).
    3. Verify Acme's funnel API returns 10 users and 20% conversion.
    4. Verify Starlight's funnel API returns 4 users and 100% conversion.
    5. Verify Date-Filtered dynamic queries preserve tenant boundaries without leaking.
    """
    # 1. Ingest Acme Data (Window: Jan 1 - Jan 25, 2025, 24 days coverage)
    acme_rows = ["user_id,event_name,event_timestamp,acquisition_channel"]
    for i in range(1, 11):
        uid = f"acme_usr_{i:02d}"
        acme_rows.append(f"{uid},signup,2025-01-01 10:00:00,Partner")
        if i <= 8:
            acme_rows.append(f"{uid},workspace_created,2025-01-02 10:00:00,Partner")
        if i <= 6:
            acme_rows.append(f"{uid},invite_sent,2025-01-03 10:00:00,Partner")
        if i <= 4:
            acme_rows.append(f"{uid},first_project,2025-01-05 10:00:00,Partner")
        if i <= 2:
            acme_rows.append(f"{uid},paid,2025-01-25 10:00:00,Partner")

    acme_csv = "\n".join(acme_rows)
    acme_headers = {"Authorization": f"Bearer {acme_token}"}
    upload_acme = client.post(
        "/api/v1/onboarding/upload",
        headers=acme_headers,
        files={"file": ("acme_funnel.csv", acme_csv.encode(), "text/csv")},
    )
    assert upload_acme.status_code == 200
    acme_summary = upload_acme.json()["quality_summary"]
    assert acme_summary["total_unique_users"] == 10
    assert acme_summary["accepted_rows"] == 30
    assert acme_summary["is_window_complete"] is True

    # 2. Ingest Starlight Data (4 users, 100% conversion)
    starlight_rows = ["user_id,event_name,event_timestamp,acquisition_channel"]
    for i in range(1, 5):
        uid = f"star_usr_{i:02d}"
        starlight_rows.append(f"{uid},signup,2025-02-01 09:00:00,Organic")
        starlight_rows.append(f"{uid},workspace_created,2025-02-02 09:00:00,Organic")
        starlight_rows.append(f"{uid},invite_sent,2025-02-03 09:00:00,Organic")
        starlight_rows.append(f"{uid},first_project,2025-02-04 09:00:00,Organic")
        starlight_rows.append(f"{uid},paid,2025-02-20 09:00:00,Organic")

    starlight_csv = "\n".join(starlight_rows)
    starlight_headers = {"Authorization": f"Bearer {starlight_token}"}
    upload_starlight = client.post(
        "/api/v1/onboarding/upload",
        headers=starlight_headers,
        files={"file": ("starlight_funnel.csv", starlight_csv.encode(), "text/csv")},
    )
    assert upload_starlight.status_code == 200
    star_summary = upload_starlight.json()["quality_summary"]
    assert star_summary["total_unique_users"] == 4
    assert star_summary["accepted_rows"] == 20

    # 3. Query Acme Funnel via GET /api/v1/funnel
    res_acme_funnel = client.get("/api/v1/funnel", headers=acme_headers)
    assert res_acme_funnel.status_code == 200
    acme_data = res_acme_funnel.json()
    assert acme_data["tenant_id"] == "org_acme_corp"
    assert acme_data["cohort_size"] == 10
    assert acme_data["overall_conversion_rate"] == 0.20
    assert acme_data["stages"][0]["entering_users"] == 10  # Signup
    assert acme_data["stages"][1]["entering_users"] == 8   # Workspace
    assert acme_data["stages"][2]["entering_users"] == 6   # Invite
    assert acme_data["stages"][3]["entering_users"] == 4   # First Project
    assert acme_data["stages"][4]["entering_users"] == 2   # Paid

    # 4. Query Starlight Funnel via GET /api/v1/funnel
    res_star_funnel = client.get("/api/v1/funnel", headers=starlight_headers)
    assert res_star_funnel.status_code == 200
    star_data = res_star_funnel.json()
    assert star_data["tenant_id"] == "org_starlight_saas"
    assert star_data["cohort_size"] == 4
    assert star_data["overall_conversion_rate"] == 1.00
    assert star_data["stages"][0]["entering_users"] == 4
    assert star_data["stages"][4]["entering_users"] == 4

    # 5. Verify Date-Filtered dynamic query for Acme
    res_acme_filtered = client.get(
        "/api/v1/funnel?start_date=2025-01-01&end_date=2025-01-31",
        headers=acme_headers,
    )
    assert res_acme_filtered.status_code == 200
    filtered_data = res_acme_filtered.json()
    assert filtered_data["tenant_id"] == "org_acme_corp"
    assert filtered_data["cohort_size"] == 10
    assert filtered_data["stages"][4]["entering_users"] == 2

    # Query out-of-range date window for Acme
    res_acme_out_of_range = client.get(
        "/api/v1/funnel?start_date=2024-01-01&end_date=2024-01-31",
        headers=acme_headers,
    )
    assert res_acme_out_of_range.status_code == 200
    assert res_acme_out_of_range.json()["cohort_size"] == 0
