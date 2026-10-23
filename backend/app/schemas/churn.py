"""Pydantic schemas for the Point-in-Time Churn Intelligence API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FeatureCoefficientItem(BaseModel):
    feature_name: str
    coefficient: float
    odds_ratio: float
    impact_direction: str
    description: str


class ModelPerformanceMetrics(BaseModel):
    roc_auc: float = Field(..., description="Out-of-sample Area Under the ROC Curve")
    pr_auc: float = Field(..., description="Out-of-sample Precision-Recall AUC (Average Precision)")
    brier_score: float = Field(..., description="Mean squared probability error (calibration measure)")
    baseline_prevalence: float = Field(..., description="Empirical 60-day churn base rate")
    train_samples: int
    test_samples: int
    baseline_model_name: str = Field("Prior Dummy Baseline", description="Name of reference baseline model")
    baseline_roc_auc: float = Field(0.50, description="Out-of-sample ROC-AUC for DummyClassifier(strategy='prior')")
    baseline_pr_auc: float = Field(..., description="Out-of-sample PR-AUC for DummyClassifier(strategy='prior')")
    baseline_brier_score: float = Field(..., description="Out-of-sample Brier score for DummyClassifier(strategy='prior')")
    evaluation_strategy: str = Field(..., description="Validation methodology and time-aware evaluation notes")
    calibration_assessment: str = Field(..., description="Empirical probability calibration assessment")


class PredictionTaskDefinition(BaseModel):
    scoring_population: str
    observation_anchor: str
    feature_window_days: int
    prediction_window_days: int
    leakage_prevention_rule: str


class RiskTierBreakdown(BaseModel):
    low_count: int
    low_pct: float
    medium_count: int
    medium_pct: float
    high_count: int
    high_pct: float
    total_scored: int
    mean_probability: float
    high_threshold: float
    medium_threshold: float


class AtRiskAccount(BaseModel):
    user_id: str
    churn_probability: float
    risk_tier: str
    days_since_last_event_at_cutoff: float
    events_in_30d: int
    distinct_events_in_30d: int
    feature_used_count: int
    plan_type: str
    company_size: str
    industry: str
    recommended_action: str
    prediction_cutoff: str = Field(default="", description="Point-in-time observation cutoff timestamp")
    exploratory_review_suggestion: str = Field(default="", description="Safe exploratory investigation suggestion")


class ChurnSummaryResponse(BaseModel):
    tenant_id: str
    organization_name: str
    task_definition: PredictionTaskDefinition
    performance: ModelPerformanceMetrics
    coefficients: list[FeatureCoefficientItem]
    risk_distribution: RiskTierBreakdown
    data_provenance_notes: str


class ChurnAccountsResponse(BaseModel):
    tenant_id: str
    organization_name: str
    total_matching: int
    accounts: list[AtRiskAccount]
