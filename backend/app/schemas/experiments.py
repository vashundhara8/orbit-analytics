"""Pydantic schemas for the Experimentation Intelligence API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class VariantMetrics(BaseModel):
    variant: str = Field(..., description="Variant name: control or treatment")
    users: int = Field(..., description="Sample size allocated to variant")
    activated_users: int = Field(..., description="Users who completed activation criterion")
    activation_rate: float = Field(..., description="Proportion of users activated")
    ci95_low: float = Field(..., description="Wald 95% confidence interval lower bound")
    ci95_high: float = Field(..., description="Wald 95% confidence interval upper bound")


class LiftMetrics(BaseModel):
    absolute_lift: float = Field(..., description="Difference in activation rate (treatment - control)")
    absolute_lift_pp: float = Field(..., description="Absolute lift in percentage points")
    relative_lift: float = Field(..., description="Relative percentage change vs control")
    ci95_difference_low_pp: float = Field(..., description="95% CI lower bound for difference (pp)")
    ci95_difference_high_pp: float = Field(..., description="95% CI upper bound for difference (pp)")


class SignificanceTest(BaseModel):
    test_name: str = "Two-Proportion Pooled Z-Test"
    z_statistic: float
    p_value: float
    alpha: float = 0.05
    is_significant: bool


class SrmDiagnostic(BaseModel):
    expected_split_pct: float = 50.0
    control_pct: float
    treatment_pct: float
    chi_square_statistic: float
    degrees_of_freedom: int = 1
    p_value: float
    has_srm: bool
    interpretation: str


class ExperimentSummaryItem(BaseModel):
    experiment_name: str
    total_users: int
    variants_count: int


class ExperimentAnalysisResponse(BaseModel):
    tenant_id: str
    organization_name: str
    experiment_name: str
    hypothesis: str
    primary_metric: str
    observation_window_days: int
    variants: list[VariantMetrics]
    lift: LiftMetrics
    significance: SignificanceTest
    srm: SrmDiagnostic
    decision_advisory: str
