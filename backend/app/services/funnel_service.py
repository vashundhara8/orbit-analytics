"""Tenant-aware analytical service for customer funnel metrics."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from backend.app.config import settings
from backend.app.schemas.funnel import (
    ChannelBenchmarkItem,
    FunnelAnalysisResponse,
    FunnelFilterApplied,
    FunnelFilterParams,
    FunnelStageItem,
)

STAGE_DEFINITIONS = [
    ("signup", "Signup", "Account registration completed", "signup_users"),
    ("workspace", "Workspace Created", "First workspace setup finalized", "workspace_users"),
    ("invite", "Invite Sent", "Teammate invitation sent", "invite_users"),
    ("project", "First Project", "Initial product project created", "project_users"),
    ("paid", "Paid Conversion", "Upgraded to active paid subscription", "paid_users"),
]


class FunnelService:
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
        # Tenant has no provisioned datasets yet
        return None

    def get_funnel_metrics(self, filters: FunnelFilterParams) -> FunnelAnalysisResponse:
        """Compute or extract tenant-scoped funnel analytics."""
        if self.tenant_data_dir is None:
            # Empty state for isolated newly provisioned tenants
            return self._build_empty_response(filters)

        # If date filtering is requested, execute dynamic DuckDB query over raw tables
        if filters.start_date or filters.end_date:
            return self._compute_date_filtered_funnel(filters)

        # Standard fast path: read validated mart_funnel
        mart_path = self.tenant_data_dir / "mart_funnel.parquet"
        if not mart_path.exists():
            return self._build_empty_response(filters)

        funnel_df = pd.read_parquet(mart_path)
        return self._process_funnel_dataframe(funnel_df, filters)

    def _compute_date_filtered_funnel(self, filters: FunnelFilterParams) -> FunnelAnalysisResponse:
        """Execute tenant-scoped parameterized DuckDB query with date filters."""
        raw_users_path = (settings.raw_dir / "dim_users.parquet").as_posix()
        raw_events_path = (settings.raw_dir / "fact_events.parquet").as_posix()
        raw_subs_path = (settings.raw_dir / "fact_subscriptions.parquet").as_posix()

        where_clauses = ["1=1"]
        params: list[str] = []

        if filters.start_date:
            where_clauses.append("u.signup_date >= ?")
            params.append(filters.start_date.isoformat())
        if filters.end_date:
            where_clauses.append("u.signup_date <= ?")
            params.append(filters.end_date.isoformat())

        where_sql = " AND ".join(where_clauses)

        query = f"""
        WITH user_steps AS (
            SELECT
                u.user_id,
                u.acquisition_channel,
                MAX(CASE WHEN e.event_name = 'signup'            THEN 1 ELSE 0 END) AS reached_signup,
                MAX(CASE WHEN e.event_name = 'workspace_created' THEN 1 ELSE 0 END) AS reached_workspace,
                MAX(CASE WHEN e.event_name = 'invite_sent'       THEN 1 ELSE 0 END) AS reached_invite,
                MAX(CASE WHEN e.event_name = 'first_project'     THEN 1 ELSE 0 END) AS reached_project,
                MAX(CASE WHEN s.paid_start_date IS NOT NULL       THEN 1 ELSE 0 END) AS reached_paid
            FROM read_parquet('{raw_users_path}') u
            LEFT JOIN read_parquet('{raw_events_path}') e        ON u.user_id = e.user_id
            LEFT JOIN read_parquet('{raw_subs_path}') s ON u.user_id = s.user_id
            WHERE {where_sql}
            GROUP BY u.user_id, u.acquisition_channel
        )
        SELECT
            acquisition_channel,
            COUNT(*)                                                    AS total_users,
            SUM(reached_signup)                                         AS signup_users,
            SUM(reached_workspace)                                      AS workspace_users,
            SUM(reached_invite)                                         AS invite_users,
            SUM(reached_project)                                        AS project_users,
            SUM(reached_paid)                                           AS paid_users,
            ROUND(SUM(reached_workspace)  * 1.0 / NULLIF(COUNT(*), 0), 4)         AS signup_to_workspace_rate,
            ROUND(SUM(reached_invite)     * 1.0 / NULLIF(SUM(reached_workspace), 0), 4) AS workspace_to_invite_rate,
            ROUND(SUM(reached_project)    * 1.0 / NULLIF(SUM(reached_invite), 0), 4)    AS invite_to_project_rate,
            ROUND(SUM(reached_paid)       * 1.0 / NULLIF(SUM(reached_project), 0), 4)   AS project_to_paid_rate,
            ROUND(SUM(reached_paid)       * 1.0 / NULLIF(COUNT(*), 0), 4)         AS overall_conversion_rate
        FROM user_steps
        GROUP BY ROLLUP(acquisition_channel);
        """

        con = duckdb.connect()
        try:
            funnel_df = con.execute(query, params).fetchdf()
        finally:
            con.close()

        return self._process_funnel_dataframe(funnel_df, filters)

    def _process_funnel_dataframe(
        self, funnel_df: pd.DataFrame, filters: FunnelFilterParams
    ) -> FunnelAnalysisResponse:
        """Transform DuckDB ROLLUP result into typed stages and channel benchmarks."""
        # Available channels (excluding NaN rollup row)
        channel_df = funnel_df.dropna(subset=["acquisition_channel"]).copy()
        available_channels = sorted(channel_df["acquisition_channel"].unique().tolist())

        # Overall aggregate row
        overall_rows = funnel_df[funnel_df["acquisition_channel"].isna()]
        if overall_rows.empty:
            return self._build_empty_response(filters)
        overall_row = overall_rows.iloc[0]
        weighted_benchmark = float(overall_row["overall_conversion_rate"] or 0.0)

        # Selected cohort row
        if filters.acquisition_channel and filters.acquisition_channel in available_channels:
            matched = funnel_df[funnel_df["acquisition_channel"] == filters.acquisition_channel]
            cohort_row = matched.iloc[0] if not matched.empty else overall_row
        else:
            cohort_row = overall_row

        total_cohort = int(cohort_row["total_users"])
        stages: list[FunnelStageItem] = []
        prev_users = total_cohort

        for idx, (step_id, name, desc, col_name) in enumerate(STAGE_DEFINITIONS, start=1):
            users = int(cohort_row[col_name]) if pd.notna(cohort_row[col_name]) else 0
            step_rate = (users / prev_users) if prev_users > 0 else 0.0
            drop_off_rate = (1.0 - step_rate) if idx > 1 else 0.0
            users_lost = (prev_users - users) if idx > 1 else 0
            cum_rate = (users / total_cohort) if total_cohort > 0 else 0.0

            stages.append(
                FunnelStageItem(
                    step_order=idx,
                    step_id=step_id,
                    name=name,
                    description=desc,
                    entering_users=users,
                    step_conversion_rate=round(step_rate, 4),
                    drop_off_rate=round(drop_off_rate, 4),
                    users_lost=users_lost,
                    cumulative_conversion_rate=round(cum_rate, 4),
                )
            )
            prev_users = users

        # Channel benchmarks
        benchmarks: list[ChannelBenchmarkItem] = []
        sorted_channels = channel_df.sort_values(
            "overall_conversion_rate", ascending=False
        ).reset_index(drop=True)

        for _, row in sorted_channels.iterrows():
            conv_rate = float(row["overall_conversion_rate"] or 0.0)
            benchmarks.append(
                ChannelBenchmarkItem(
                    channel=str(row["acquisition_channel"]),
                    total_signups=int(row["total_users"]),
                    paid_customers=int(row["paid_users"]),
                    conversion_rate=round(conv_rate, 4),
                    variance_vs_benchmark=round(conv_rate - weighted_benchmark, 4),
                )
            )

        overall_conv = float(cohort_row["overall_conversion_rate"] or 0.0)

        return FunnelAnalysisResponse(
            tenant_id=self.tenant_id,
            organization_name=self.org_name,
            filter_applied=FunnelFilterApplied(
                acquisition_channel=filters.acquisition_channel,
                start_date=filters.start_date,
                end_date=filters.end_date,
            ),
            cohort_size=total_cohort,
            overall_conversion_rate=round(overall_conv, 4),
            stages=stages,
            channel_benchmarks=benchmarks,
            available_channels=available_channels,
        )

    def _build_empty_response(self, filters: FunnelFilterParams) -> FunnelAnalysisResponse:
        """Generate a structured zeroed response for unpopulated tenant workspaces."""
        empty_stages = [
            FunnelStageItem(
                step_order=idx,
                step_id=step_id,
                name=name,
                description=desc,
                entering_users=0,
                step_conversion_rate=0.0,
                drop_off_rate=0.0,
                users_lost=0,
                cumulative_conversion_rate=0.0,
            )
            for idx, (step_id, name, desc, _) in enumerate(STAGE_DEFINITIONS, start=1)
        ]
        return FunnelAnalysisResponse(
            tenant_id=self.tenant_id,
            organization_name=self.org_name,
            filter_applied=FunnelFilterApplied(
                acquisition_channel=filters.acquisition_channel,
                start_date=filters.start_date,
                end_date=filters.end_date,
            ),
            cohort_size=0,
            overall_conversion_rate=0.0,
            stages=empty_stages,
            channel_benchmarks=[],
            available_channels=[],
        )
