"""Verification script for Phase 1: End-to-end export & JSON consistency check."""

import csv
import io

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)
demo_token = client.get("/api/v1/auth/demo-token?tenant_id=org_orbit_demo").json()["access_token"]
headers = {"Authorization": f"Bearer {demo_token}"}

# 1. Compare Funnel JSON with Funnel CSV Export
funnel_json = client.get("/api/v1/funnel", headers=headers).json()
funnel_csv_text = client.get("/api/v1/funnel/export", headers=headers).text
reader = list(csv.DictReader(io.StringIO(funnel_csv_text)))

assert len(reader) == len(funnel_json["stages"]), f"Stages count mismatch: {len(reader)} vs {len(funnel_json['stages'])}"
for csv_row, json_stage in zip(reader, funnel_json["stages"], strict=True):
    assert int(csv_row["step_order"]) == json_stage["step_order"]
    assert csv_row["step_id"] == json_stage["step_id"]
    assert csv_row["name"] == json_stage["name"]
    assert int(csv_row["entering_users"]) == json_stage["entering_users"]
    assert int(csv_row["users_lost"]) == json_stage["users_lost"]
    assert abs(float(csv_row["step_conversion_rate"]) - json_stage["step_conversion_rate"]) < 1e-4
    assert abs(float(csv_row["cumulative_conversion_rate"]) - json_stage["cumulative_conversion_rate"]) < 1e-4
print("✓ Funnel CSV export matches dashboard JSON stages perfectly.")

# 2. Compare Churn Accounts JSON with Churn CSV Export
churn_json = client.get("/api/v1/churn/accounts?limit=25", headers=headers).json()
churn_csv_text = client.get("/api/v1/churn/export?limit=25", headers=headers).text
churn_reader = list(csv.DictReader(io.StringIO(churn_csv_text)))

assert len(churn_reader) == len(churn_json["accounts"]), f"Account count mismatch: {len(churn_reader)} vs {len(churn_json['accounts'])}"
for csv_row, json_acc in zip(churn_reader, churn_json["accounts"], strict=True):
    assert csv_row["user_id"] == json_acc["user_id"]
    assert abs(float(csv_row["churn_probability"]) - json_acc["churn_probability"]) < 1e-4
    assert csv_row["risk_tier"] == json_acc["risk_tier"]
    assert abs(float(csv_row["days_since_last_event_at_cutoff"]) - json_acc["days_since_last_event_at_cutoff"]) < 0.2
    assert csv_row["recommended_action"] == json_acc["recommended_action"]
    assert csv_row["exploratory_review_suggestion"] == json_acc["exploratory_review_suggestion"]
print("✓ Churn accounts CSV export matches dashboard JSON accounts perfectly.")

