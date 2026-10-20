"""Tenant-aware analytical service for weekly cohort retention matrices."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.app.config import settings
from backend.app.schemas.cohorts import (
    CohortCellItem,
    CohortMilestones,
    CohortRetentionParams,
    CohortRetentionResponse,
    CohortRowItem,
)


class CohortService:
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

    def get_cohort_retention(self, params: CohortRetentionParams) -> CohortRetentionResponse:
        """Calculate the weekly cohort retention matrix with elapsed-period masking."""
        if self.tenant_data_dir is None:
            return self._build_empty_response(params)

        mart_path = self.tenant_data_dir / "mart_cohort_retention.parquet"
        if not mart_path.exists():
            return self._build_empty_response(params)

        df = pd.read_parquet(mart_path)
        if df.empty:
            return self._build_empty_response(params)

        # Ensure datetime format for cohort_week
        df["cohort_week_dt"] = pd.to_datetime(df["cohort_week"])
        df["cohort_week_str"] = df["cohort_week_dt"].dt.strftime("%Y-%m-%d")

        # Extract initial cohort sizes from weeks_since_signup == 0
        w0_df = df[df["weeks_since_signup"] == 0][["cohort_week_str", "cohort_size"]].drop_duplicates()

        # Apply minimum cohort size filter
        eligible_cohorts = w0_df[w0_df["cohort_size"] >= params.min_cohort_size]["cohort_week_str"].tolist()
        if not eligible_cohorts:
            return self._build_empty_response(params)

        # Filter to eligible cohorts and restrict horizon
        filtered_df = df[
            df["cohort_week_str"].isin(eligible_cohorts)
            & (df["weeks_since_signup"] <= params.max_weeks)
        ].copy()

        # Get unique eligible cohorts in chronological order, then select the most recent N
        unique_weeks = sorted(filtered_df["cohort_week_str"].unique().tolist())
        selected_weeks = unique_weeks[-params.num_cohorts :]

        filtered_df = filtered_df[filtered_df["cohort_week_str"].isin(selected_weeks)]

        # Build structured matrix rows
        cohort_rows: list[CohortRowItem] = []
        w1_rates: list[float] = []
        w4_rates: list[float] = []
        w8_rates: list[float] = []
        w12_rates: list[float] = []

        for week_str in selected_weeks:
            cohort_data = filtered_df[filtered_df["cohort_week_str"] == week_str]
            c_size_series = cohort_data["cohort_size"]
            c_size = int(c_size_series.iloc[0]) if not c_size_series.empty else 0

            # Build cell lookup by week
            week_map = {
                int(row["weeks_since_signup"]): (
                    int(row["active_users"]) if pd.notna(row["active_users"]) else None,
                    float(row["retention_rate"]) if pd.notna(row["retention_rate"]) else None,
                )
                for _, row in cohort_data.iterrows()
            }

            cells: list[CohortCellItem] = []
            for w in range(params.max_weeks + 1):
                if w in week_map:
                    act_u, ret_r = week_map[w]
                    cells.append(
                        CohortCellItem(
                            weeks_since_signup=w,
                            active_users=act_u,
                            retention_rate=round(ret_r, 4) if ret_r is not None else None,
                        )
                    )
                    # Accumulate for milestone averages if rate is valid
                    if ret_r is not None:
                        if w == 1:
                            w1_rates.append(ret_r)
                        elif w == 4:
                            w4_rates.append(ret_r)
                        elif w == 8:
                            w8_rates.append(ret_r)
                        elif w == 12:
                            w12_rates.append(ret_r)
                else:
                    # Incomplete / unobserved future period
                    cells.append(
                        CohortCellItem(
                            weeks_since_signup=w,
                            active_users=None,
                            retention_rate=None,
                        )
                    )

            cohort_rows.append(
                CohortRowItem(
                    cohort_week=week_str,
                    cohort_size=c_size,
                    cells=cells,
                )
            )

        milestones = CohortMilestones(
            w1_retention_avg=round(float(pd.Series(w1_rates).mean()), 4) if w1_rates else None,
            w4_retention_avg=round(float(pd.Series(w4_rates).mean()), 4) if w4_rates else None,
            w8_retention_avg=round(float(pd.Series(w8_rates).mean()), 4) if w8_rates else None,
            w12_retention_avg=round(float(pd.Series(w12_rates).mean()), 4) if w12_rates else None,
        )

        return CohortRetentionResponse(
            tenant_id=self.tenant_id,
            organization_name=self.org_name,
            num_cohorts_returned=len(cohort_rows),
            max_weeks_horizon=params.max_weeks,
            min_cohort_size_filter=params.min_cohort_size,
            milestones=milestones,
            cohorts=cohort_rows,
        )

    def _build_empty_response(self, params: CohortRetentionParams) -> CohortRetentionResponse:
        """Return zeroed response for empty or isolated workspaces."""
        return CohortRetentionResponse(
            tenant_id=self.tenant_id,
            organization_name=self.org_name,
            num_cohorts_returned=0,
            max_weeks_horizon=params.max_weeks,
            min_cohort_size_filter=params.min_cohort_size,
            milestones=CohortMilestones(),
            cohorts=[],
        )
