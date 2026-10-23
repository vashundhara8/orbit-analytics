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


# ── Revenue & Billing Intelligence Schemas ──────────────────────────────────


class VariantRevenueMetrics(BaseModel):
    variant: str = Field(..., description="Variant name: control or treatment")
    assigned_users: int = Field(..., description="Total users allocated (Intention-To-Treat)")
    paid_conversions: int = Field(..., description="Users who converted to paid within observation window")
    paid_conversion_rate: float = Field(..., description="Proportion of assigned users converted to paid")
    ci95_conversion_low: float = Field(..., description="Wald 95% CI lower bound for conversion rate")
    ci95_conversion_high: float = Field(..., description="Wald 95% CI upper bound for conversion rate")
    active_subscribers: int = Field(..., description="Active paying subscribers with mrr > 0 at snapshot")
    churned_subscribers: int = Field(..., description="Subscribers who cancelled after converting")
    post_conversion_churn_rate: float = Field(..., description="Churn rate among converted paid users")
    total_mrr: float = Field(..., description="Active Snapshot MRR from Experiment Cohort at end-of-simulation snapshot (not cumulative recognized revenue or cash collected)")
    arpu: float = Field(..., description="Average Active Snapshot MRR per assigned user (total_mrr / assigned_users)")
    arppu: float = Field(..., description="Average Active Snapshot MRR per paying customer (total_mrr / paid_conversions)")


class RevenueLiftMetrics(BaseModel):
    absolute_conversion_lift: float = Field(..., description="Difference in conversion rate (treatment - control)")
    absolute_conversion_lift_pp: float = Field(..., description="Absolute conversion lift in percentage points")
    relative_conversion_lift: float = Field(..., description="Relative percentage change in conversion vs control")
    ci95_conversion_diff_low_pp: float = Field(..., description="95% CI lower bound for conversion difference (pp)")
    ci95_conversion_diff_high_pp: float = Field(..., description="95% CI upper bound for conversion difference (pp)")
    arpu_diff: float = Field(..., description="Difference in ARPU (treatment - control)")
    arpu_relative_lift: float = Field(..., description="Relative percentage change in ARPU vs control")
    ci95_arpu_diff_low: float = Field(..., description="95% CI lower bound for ARPU difference ($)")
    ci95_arpu_diff_high: float = Field(..., description="95% CI upper bound for ARPU difference ($)")


class RevenueSignificanceTest(BaseModel):
    conversion_test_name: str = "Two-Proportion Pooled Z-Test"
    conversion_z_stat: float
    conversion_p_value: float
    conversion_is_significant: bool
    arpu_test_name: str = "Welch's Two-Sample T-Test"
    arpu_t_stat: float
    arpu_p_value: float
    arpu_is_significant: bool
    alpha: float = 0.05


class TrialSubpopulationMetrics(BaseModel):
    control_trial_users: int
    control_trial_conversions: int
    control_trial_conversion_rate: float
    treatment_trial_users: int
    treatment_trial_conversions: int
    treatment_trial_conversion_rate: float
    trial_conversion_z_stat: float
    trial_conversion_p_value: float
    trial_conversion_is_significant: bool


class RevenueDiagnostics(BaseModel):
    srm_p_value: float
    has_srm: bool
    duplicate_assignments_detected: int = 0
    missing_subscription_records: int = 0
    pre_assignment_conversions_detected: int = 0
    observation_window_complete: bool = True
    window_days: int = 35


class ExperimentRevenueAnalysisResponse(BaseModel):
    tenant_id: str
    organization_name: str
    experiment_name: str
    hypothesis: str
    primary_metric: str
    observation_window_days: int
    evaluated_population: str
    variants: list[VariantRevenueMetrics]
    lift: RevenueLiftMetrics
    significance: RevenueSignificanceTest
    trial_subpopulation: TrialSubpopulationMetrics
    diagnostics: RevenueDiagnostics
    decision_advisory: str
    causality_disclosure: str
