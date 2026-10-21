"""Tenant-aware analytical service for experiment results and statistical inference."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2, norm
from statsmodels.stats.proportion import proportions_ztest

from backend.app.config import settings
from backend.app.schemas.experiments import (
    ExperimentAnalysisResponse,
    ExperimentSummaryItem,
    LiftMetrics,
    SignificanceTest,
    SrmDiagnostic,
    VariantMetrics,
)


class ExperimentService:
    def __init__(self, tenant_id: str, org_name: str) -> None:
        self.tenant_id = tenant_id
        self.org_name = org_name
        self.tenant_data_dir = self._resolve_tenant_storage(tenant_id)

    def _resolve_tenant_storage(self, tenant_id: str) -> Path | None:
        """Resolve storage path enforcing strict tenant isolation boundaries."""
        if tenant_id == settings.default_tenant_id:
            return settings.processed_dir

        tenant_path = settings.data_dir / "tenants" / tenant_id
        if tenant_path.exists():
            return tenant_path
        return None

    def list_experiments(self) -> list[ExperimentSummaryItem]:
        """List active experiments registered for the tenant."""
        if self.tenant_data_dir is None:
            return []

        mart_path = self.tenant_data_dir / "mart_experiment_results.parquet"
        if not mart_path.exists():
            return []

        df = pd.read_parquet(mart_path)
        if df.empty or "experiment_name" not in df.columns:
            return []

        items: list[ExperimentSummaryItem] = []
        for name, group in df.groupby("experiment_name"):
            items.append(
                ExperimentSummaryItem(
                    experiment_name=str(name),
                    total_users=int(group["users"].sum()),
                    variants_count=len(group),
                )
            )
        return items

    def get_experiment_analysis(self, experiment_name: str = "onboarding_v2") -> ExperimentAnalysisResponse:
        """Compute statistical hypothesis test, confidence intervals, and SRM diagnostics."""
        if self.tenant_data_dir is None:
            return self._build_empty_response(experiment_name)

        mart_path = self.tenant_data_dir / "mart_experiment_results.parquet"
        if not mart_path.exists():
            return self._build_empty_response(experiment_name)

        df = pd.read_parquet(mart_path)
        matched = df[df["experiment_name"] == experiment_name]
        if matched.empty:
            return self._build_empty_response(experiment_name)

        control_rows = matched[matched["variant"] == "control"]
        treatment_rows = matched[matched["variant"] == "treatment"]

        if control_rows.empty or treatment_rows.empty:
            return self._build_empty_response(
                experiment_name,
                advisory="Experiment data is incomplete: missing control or treatment variant. Cannot perform hypothesis testing.",
            )

        c_row = control_rows.iloc[0]
        t_row = treatment_rows.iloc[0]

        control_n = int(c_row["users"]) if pd.notna(c_row["users"]) else 0
        control_act = round(float(c_row["activated_users"])) if pd.notna(c_row["activated_users"]) else 0
        control_p = float(c_row["activation_rate"]) if pd.notna(c_row["activation_rate"]) else 0.0

        treatment_n = int(t_row["users"]) if pd.notna(t_row["users"]) else 0
        treatment_act = round(float(t_row["activated_users"])) if pd.notna(t_row["activated_users"]) else 0
        treatment_p = float(t_row["activation_rate"]) if pd.notna(t_row["activation_rate"]) else 0.0

        total_n = control_n + treatment_n
        if control_n <= 0 or treatment_n <= 0 or total_n < 10:
            return self._build_empty_response(
                experiment_name,
                advisory=f"Insufficient sample size (control n={control_n}, treatment n={treatment_n}). At least 10 observations required for statistical inference.",
            )

        # 95% Wald CI for single proportions: p +/- 1.96 * sqrt(p(1-p)/n)
        se_c = np.sqrt(control_p * (1.0 - control_p) / control_n) if control_n > 0 else 0.0
        se_t = np.sqrt(treatment_p * (1.0 - treatment_p) / treatment_n) if treatment_n > 0 else 0.0

        ci_c_low = max(0.0, control_p - 1.96 * se_c)
        ci_c_high = min(1.0, control_p + 1.96 * se_c)

        ci_t_low = max(0.0, treatment_p - 1.96 * se_t)
        ci_t_high = min(1.0, treatment_p + 1.96 * se_t)

        variants = [
            VariantMetrics(
                variant="control",
                users=control_n,
                activated_users=control_act,
                activation_rate=round(control_p, 4),
                ci95_low=round(float(ci_c_low), 4),
                ci95_high=round(float(ci_c_high), 4),
            ),
            VariantMetrics(
                variant="treatment",
                users=treatment_n,
                activated_users=treatment_act,
                activation_rate=round(treatment_p, 4),
                ci95_low=round(float(ci_t_low), 4),
                ci95_high=round(float(ci_t_high), 4),
            ),
        ]

        # Lift calculations
        abs_lift = treatment_p - control_p
        abs_lift_pp = abs_lift * 100.0
        rel_lift = (abs_lift / control_p) if control_p > 0 else 0.0

        # 95% CI for difference in proportions (Wald unpooled standard error)
        se_diff = (
            np.sqrt((control_p * (1.0 - control_p) / control_n) + (treatment_p * (1.0 - treatment_p) / treatment_n))
            if control_n > 0 and treatment_n > 0
            else 0.0
        )
        ci_diff_half_pp = 1.96 * se_diff * 100.0
        ci_diff_low_pp = abs_lift_pp - ci_diff_half_pp
        ci_diff_high_pp = abs_lift_pp + ci_diff_half_pp

        lift_metrics = LiftMetrics(
            absolute_lift=round(abs_lift, 4),
            absolute_lift_pp=round(abs_lift_pp, 2),
            relative_lift=round(rel_lift, 4),
            ci95_difference_low_pp=round(ci_diff_low_pp, 2),
            ci95_difference_high_pp=round(ci_diff_high_pp, 2),
        )

        # Pooled Two-Proportion Z-Test
        if control_act == 0 and treatment_act == 0:
            z_stat = 0.0
            p_val = 1.0
        else:
            successes = np.array([treatment_act, control_act])
            observations = np.array([treatment_n, control_n])
            try:
                z_stat, p_val = proportions_ztest(successes, observations)
                z_stat = float(z_stat)
                p_val = float(p_val)
            except Exception:
                # Fallback exact calculation
                p_pool = (treatment_act + control_act) / total_n if total_n > 0 else 0.0
                se_pool = np.sqrt(p_pool * (1.0 - p_pool) * (1.0 / treatment_n + 1.0 / control_n))
                z_stat = float((treatment_p - control_p) / se_pool) if se_pool > 0 else 0.0
                p_val = float(2.0 * (1.0 - norm.cdf(abs(z_stat))))

        significance = SignificanceTest(
            test_name="Two-Proportion Pooled Z-Test",
            z_statistic=round(z_stat, 4),
            p_value=round(p_val, 7),
            alpha=0.05,
            is_significant=bool(p_val < 0.05),
        )

        # Sample Ratio Mismatch (SRM) diagnostic (expected 50/50 split)
        expected_split = total_n / 2.0
        chi_sq_stat = float(
            ((control_n - expected_split) ** 2 / expected_split)
            + ((treatment_n - expected_split) ** 2 / expected_split)
        )
        srm_p_value = float(1.0 - chi2.cdf(chi_sq_stat, df=1))
        has_srm = bool(srm_p_value < 0.01)

        c_pct = (control_n / total_n * 100.0) if total_n > 0 else 0.0
        t_pct = (treatment_n / total_n * 100.0) if total_n > 0 else 0.0

        if has_srm:
            srm_interp = (
                f"Severe Sample Ratio Mismatch detected (chi2={chi_sq_stat:.2f}, p={srm_p_value:.4e} < 0.01). "
                f"Traffic allocation ({c_pct:.1f}% vs {t_pct:.1f}%) deviates significantly from 50/50. "
                "Results are biased by technical assignment failure or tracking loss; inference is invalid."
            )
        else:
            srm_interp = (
                f"Sample Ratio Mismatch check passed (chi2={chi_sq_stat:.2f}, p={srm_p_value:.4f} >= 0.01). "
                f"Traffic allocation ({c_pct:.1f}% control vs {t_pct:.1f}% treatment) aligns with the expected 50/50 assignment."
            )

        srm_diag = SrmDiagnostic(
            expected_split_pct=50.0,
            control_pct=round(c_pct, 1),
            treatment_pct=round(t_pct, 1),
            chi_square_statistic=round(chi_sq_stat, 4),
            degrees_of_freedom=1,
            p_value=round(srm_p_value, 4),
            has_srm=has_srm,
            interpretation=srm_interp,
        )

        p_str = "< 0.001" if p_val < 0.001 else f"= {p_val:.4f}"
        if has_srm:
            advisory = (
                f"CRITICAL DIAGNOSTIC WARNING: Sample Ratio Mismatch (SRM) detected (p = {srm_p_value:.4e} < 0.01, chi2 = {chi_sq_stat:.2f}). "
                "The sample allocation between control and treatment deviates significantly from the expected 50/50 split. "
                "Regardless of the observed z-score or p-value, this experiment CANNOT be declared a winner or used for decision-making. "
                "Investigate assignment bucketing, redirect latency, or user filtering defects before re-running."
            )
        elif significance.is_significant and abs_lift > 0:
            advisory = (
                f"Statistically significant positive lift (+{abs_lift_pp:.2f} pp absolute, +{rel_lift * 100:.1f}% relative) "
                f"observed in 7-day workspace activation (z = {z_stat:.2f}, p {p_str}). "
                f"The 95% confidence interval for true population lift [{ci_diff_low_pp:+.2f} pp, {ci_diff_high_pp:+.2f} pp] "
                "strictly excludes zero. Note: statistical significance establishes evidence against the null under this specific design, "
                "but does not automatically guarantee overall business value or long-term retention. "
                "Evaluate downstream metrics and operational capacity before 100% rollout."
            )
        elif significance.is_significant and abs_lift < 0:
            advisory = (
                f"Statistically significant negative regression ({abs_lift_pp:.2f} pp absolute, {rel_lift * 100:.1f}% relative) "
                f"detected in 7-day workspace activation (z = {z_stat:.2f}, p {p_str}). "
                f"The 95% confidence interval [{ci_diff_low_pp:+.2f} pp, {ci_diff_high_pp:+.2f} pp] strictly excludes zero in the negative direction. "
                "Treatment variant performed significantly worse than control. Do not roll out treatment."
            )
        else:
            advisory = (
                f"Observed difference ({abs_lift_pp:+.2f} pp absolute) is not statistically significant at alpha = 0.05 "
                f"(z = {z_stat:.2f}, p = {p_val:.4f}). The 95% confidence interval [{ci_diff_low_pp:+.2f} pp, {ci_diff_high_pp:+.2f} pp] "
                "spans across zero. Insufficient evidence to reject the null hypothesis; observed variation is consistent with random chance. "
                "Do not launch treatment on assumption of positive performance."
            )

        return ExperimentAnalysisResponse(
            tenant_id=self.tenant_id,
            organization_name=self.org_name,
            experiment_name=experiment_name,
            hypothesis="Streamlined 3-step onboarding checklist increases 7-day workspace activation vs multi-page modal tour.",
            primary_metric="7-day Workspace Activation Rate (workspace_created within 7 days of assignment)",
            observation_window_days=7,
            variants=variants,
            lift=lift_metrics,
            significance=significance,
            srm=srm_diag,
            decision_advisory=advisory,
        )

    def _build_empty_response(
        self,
        experiment_name: str,
        advisory: str = "Workspace is empty or has no active experiment data.",
    ) -> ExperimentAnalysisResponse:
        """Return zeroed response for isolated unpopulated tenant workspaces."""
        return ExperimentAnalysisResponse(
            tenant_id=self.tenant_id,
            organization_name=self.org_name,
            experiment_name=experiment_name,
            hypothesis="No experiment data provisioned for this workspace.",
            primary_metric="7-day Workspace Activation Rate",
            observation_window_days=7,
            variants=[],
            lift=LiftMetrics(
                absolute_lift=0.0,
                absolute_lift_pp=0.0,
                relative_lift=0.0,
                ci95_difference_low_pp=0.0,
                ci95_difference_high_pp=0.0,
            ),
            significance=SignificanceTest(
                test_name="Two-Proportion Pooled Z-Test",
                z_statistic=0.0,
                p_value=1.0,
                alpha=0.05,
                is_significant=False,
            ),
            srm=SrmDiagnostic(
                expected_split_pct=50.0,
                control_pct=0.0,
                treatment_pct=0.0,
                chi_square_statistic=0.0,
                degrees_of_freedom=1,
                p_value=1.0,
                has_srm=False,
                interpretation="No experiment traffic recorded for this tenant.",
            ),
            decision_advisory=advisory,
        )
