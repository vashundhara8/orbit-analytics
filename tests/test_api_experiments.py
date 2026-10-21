"""Integration tests for Experimentation Intelligence API: hypothesis tests, SRM, and tenant isolation."""

from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.auth.models import AuthenticatedUser, UserRole
from backend.app.auth.security import create_access_token
from backend.app.config import settings
from backend.app.main import app
from backend.app.services.experiment_service import ExperimentService

client = TestClient(app)


@pytest.fixture
def demo_token() -> str:
    user = AuthenticatedUser(
        user_id="usr_test_analyst",
        email="analyst@orbitanalytics.io",
        tenant_id=settings.default_tenant_id,
        role=UserRole.ANALYST,
        organization_name=settings.default_tenant_name,
    )
    return create_access_token(user)


@pytest.fixture
def acme_token() -> str:
    user = AuthenticatedUser(
        user_id="usr_acme_analyst",
        email="analyst@acme.com",
        tenant_id="org_acme_corp",
        role=UserRole.ANALYST,
        organization_name="Acme Technologies Inc.",
    )
    return create_access_token(user)


def test_list_experiments_success(demo_token: str):
    headers = {"Authorization": f"Bearer {demo_token}"}
    response = client.get("/api/v1/experiments", headers=headers)
    assert response.status_code == 200

    experiments = response.json()
    assert len(experiments) >= 1
    names = [e["experiment_name"] for e in experiments]
    assert "onboarding_v2" in names


def test_get_experiment_analysis_onboarding_v2(demo_token: str):
    headers = {"Authorization": f"Bearer {demo_token}"}
    response = client.get("/api/v1/experiments/onboarding_v2", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["experiment_name"] == "onboarding_v2"
    assert data["tenant_id"] == settings.default_tenant_id

    # Verify variants
    variants = data["variants"]
    assert len(variants) == 2

    control = next(v for v in variants if v["variant"] == "control")
    treatment = next(v for v in variants if v["variant"] == "treatment")

    assert control["users"] == 10095
    assert control["activated_users"] == 6791
    assert control["activation_rate"] == 0.6727

    assert treatment["users"] == 9905
    assert treatment["activated_users"] == 6986
    assert treatment["activation_rate"] == 0.7053

    # Verify lift metrics
    lift = data["lift"]
    assert lift["absolute_lift_pp"] == 3.26
    assert abs(lift["relative_lift"] - 0.0484) < 0.005  # ~ +4.84%

    # 95% Confidence Interval for difference strictly excludes zero
    assert lift["ci95_difference_low_pp"] > 1.5
    assert lift["ci95_difference_high_pp"] < 5.0
    assert lift["ci95_difference_low_pp"] < lift["ci95_difference_high_pp"]

    # Significance test
    sig = data["significance"]
    assert sig["is_significant"] is True
    assert sig["z_statistic"] > 4.5
    assert sig["p_value"] < 0.001

    # SRM check passes (expected 50/50, actual 50.5% vs 49.5%, p ~ 0.179 >= 0.01)
    srm = data["srm"]
    assert srm["has_srm"] is False
    assert srm["p_value"] >= 0.01
    assert "Sample Ratio Mismatch check passed" in srm["interpretation"]


def test_unknown_experiment_empty_response(demo_token: str):
    headers = {"Authorization": f"Bearer {demo_token}"}
    response = client.get("/api/v1/experiments/nonexistent_experiment_xyz", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["variants"]) == 0
    assert data["lift"]["absolute_lift"] == 0.0


def test_unauthorized_experiments_access():
    response = client.get("/api/v1/experiments")
    assert response.status_code == 401


def test_tenant_isolation_experiments(acme_token: str):
    headers = {"Authorization": f"Bearer {acme_token}"}
    response = client.get("/api/v1/experiments/onboarding_v2", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["tenant_id"] == "org_acme_corp"
    assert len(data["variants"]) == 0
    assert data["lift"]["absolute_lift"] == 0.0


def test_experiment_zero_conversion_rate(monkeypatch, tmp_path):
    """Verify zero conversions in both variants do not raise ZeroDivisionError and yield defined relative lift."""
    df_zero = pd.DataFrame([
        {"experiment_name": "zero_exp", "variant": "control", "users": 1000, "activated_users": 0, "activation_rate": 0.0},
        {"experiment_name": "zero_exp", "variant": "treatment", "users": 1000, "activated_users": 0, "activation_rate": 0.0},
    ])
    parquet_path = tmp_path / "mart_experiment_results.parquet"
    df_zero.to_parquet(parquet_path)

    svc = ExperimentService(tenant_id="test_tenant", org_name="Test Org")
    monkeypatch.setattr(svc, "tenant_data_dir", tmp_path)

    res = svc.get_experiment_analysis("zero_exp")
    assert res.lift.relative_lift == 0.0
    assert res.lift.absolute_lift == 0.0
    assert res.significance.z_statistic == 0.0
    assert res.significance.p_value == 1.0
    assert res.significance.is_significant is False


def test_experiment_missing_group_handling(monkeypatch, tmp_path):
    """Verify missing treatment group is gracefully handled with advisory."""
    df_missing = pd.DataFrame([
        {"experiment_name": "missing_exp", "variant": "control", "users": 1000, "activated_users": 500, "activation_rate": 0.5},
    ])
    parquet_path = tmp_path / "mart_experiment_results.parquet"
    df_missing.to_parquet(parquet_path)

    svc = ExperimentService(tenant_id="test_tenant", org_name="Test Org")
    monkeypatch.setattr(svc, "tenant_data_dir", tmp_path)

    res = svc.get_experiment_analysis("missing_exp")
    assert len(res.variants) == 0
    assert "missing control or treatment variant" in res.decision_advisory


def test_experiment_insufficient_sample_size(monkeypatch, tmp_path):
    """Verify small sample size (< 10 total) is rejected gracefully."""
    df_small = pd.DataFrame([
        {"experiment_name": "small_exp", "variant": "control", "users": 3, "activated_users": 1, "activation_rate": 0.3333},
        {"experiment_name": "small_exp", "variant": "treatment", "users": 4, "activated_users": 2, "activation_rate": 0.5},
    ])
    parquet_path = tmp_path / "mart_experiment_results.parquet"
    df_small.to_parquet(parquet_path)

    svc = ExperimentService(tenant_id="test_tenant", org_name="Test Org")
    monkeypatch.setattr(svc, "tenant_data_dir", tmp_path)

    res = svc.get_experiment_analysis("small_exp")
    assert len(res.variants) == 0
    assert "Insufficient sample size" in res.decision_advisory


def test_experiment_srm_diagnostic_warning(monkeypatch, tmp_path):
    """Verify severe sample ratio mismatch triggers SRM warning and prevents claiming a winner."""
    # 8,000 control vs 2,000 treatment -> extreme SRM
    df_srm = pd.DataFrame([
        {"experiment_name": "srm_exp", "variant": "control", "users": 8000, "activated_users": 4000, "activation_rate": 0.50},
        {"experiment_name": "srm_exp", "variant": "treatment", "users": 2000, "activated_users": 1400, "activation_rate": 0.70},
    ])
    parquet_path = tmp_path / "mart_experiment_results.parquet"
    df_srm.to_parquet(parquet_path)

    svc = ExperimentService(tenant_id="test_tenant", org_name="Test Org")
    monkeypatch.setattr(svc, "tenant_data_dir", tmp_path)

    res = svc.get_experiment_analysis("srm_exp")
    assert res.srm.has_srm is True
    assert res.srm.p_value < 0.001
    assert "CRITICAL DIAGNOSTIC WARNING: Sample Ratio Mismatch (SRM) detected" in res.decision_advisory
    assert "CANNOT be declared a winner" in res.decision_advisory


def test_experiment_inconclusive_result(monkeypatch, tmp_path):
    """Verify non-significant result retains null hypothesis cautiously."""
    # Identical rates -> p-value near 1.0
    df_inconc = pd.DataFrame([
        {"experiment_name": "inconc_exp", "variant": "control", "users": 500, "activated_users": 250, "activation_rate": 0.50},
        {"experiment_name": "inconc_exp", "variant": "treatment", "users": 500, "activated_users": 252, "activation_rate": 0.504},
    ])
    parquet_path = tmp_path / "mart_experiment_results.parquet"
    df_inconc.to_parquet(parquet_path)

    svc = ExperimentService(tenant_id="test_tenant", org_name="Test Org")
    monkeypatch.setattr(svc, "tenant_data_dir", tmp_path)

    res = svc.get_experiment_analysis("inconc_exp")
    assert res.significance.is_significant is False
    assert res.significance.p_value > 0.05
    assert "not statistically significant" in res.decision_advisory
    assert "Insufficient evidence to reject the null hypothesis" in res.decision_advisory


def test_experiment_negative_regression(monkeypatch, tmp_path):
    """Verify significant negative effect is clearly identified as a regression, not a winner."""
    # Treatment performs significantly worse than control
    df_neg = pd.DataFrame([
        {"experiment_name": "neg_exp", "variant": "control", "users": 2000, "activated_users": 1400, "activation_rate": 0.70},
        {"experiment_name": "neg_exp", "variant": "treatment", "users": 2000, "activated_users": 1000, "activation_rate": 0.50},
    ])
    parquet_path = tmp_path / "mart_experiment_results.parquet"
    df_neg.to_parquet(parquet_path)

    svc = ExperimentService(tenant_id="test_tenant", org_name="Test Org")
    monkeypatch.setattr(svc, "tenant_data_dir", tmp_path)

    res = svc.get_experiment_analysis("neg_exp")
    assert res.significance.is_significant is True
    assert res.lift.absolute_lift < 0
    assert "Statistically significant negative regression" in res.decision_advisory
    assert "Treatment variant performed significantly worse" in res.decision_advisory
