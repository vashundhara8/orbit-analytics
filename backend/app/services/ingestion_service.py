"""Customer data ingestion service.

Validates uploaded CSV datasets, enforces tenant boundaries, detects duplicates/rejections,
and materializes tenant-isolated raw and analytical Parquet marts using DuckDB.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
from fastapi import HTTPException, status

from backend.app.config import settings
from backend.app.schemas.onboarding import (
    DataQualitySummary,
    IngestionStatusResponse,
    IngestionUploadResponse,
)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB limit
MAX_ROW_COUNT = 100_000
MIN_VALID_YEAR = 2015

CANONICAL_EVENTS: dict[str, str] = {
    "signup": "signup",
    "user_signup": "signup",
    "sign_up": "signup",
    "workspace_created": "workspace_created",
    "workspace": "workspace_created",
    "create_workspace": "workspace_created",
    "invite_sent": "invite_sent",
    "invite": "invite_sent",
    "send_invite": "invite_sent",
    "first_project": "first_project",
    "project": "first_project",
    "create_project": "first_project",
    "paid": "paid",
    "upgrade": "paid",
    "subscription_paid": "paid",
    "checkout_completed": "paid",
}


class IngestionService:
    """Manages secure, tenant-isolated data validation and ingestion."""

    def __init__(self, tenant_id: str, org_name: str):
        self.tenant_id = tenant_id
        self.org_name = org_name
        self.tenant_raw_dir = settings.data_dir / "tenants" / tenant_id / "raw"
        self.tenant_processed_dir = settings.data_dir / "tenants" / tenant_id / "processed"
        self.status_file = settings.data_dir / "tenants" / tenant_id / "ingestion_status.json"

    def get_status(self) -> IngestionStatusResponse:
        """Retrieve the latest ingestion status and data quality metrics for this tenant."""
        if not self.status_file.exists():
            return IngestionStatusResponse(
                tenant_id=self.tenant_id,
                organization_name=self.org_name,
                has_data=False,
                last_ingested_at=None,
                filename=None,
                quality_summary=None,
            )

        try:
            with open(self.status_file, encoding="utf-8") as f:
                data = json.load(f)
            return IngestionStatusResponse(
                tenant_id=self.tenant_id,
                organization_name=self.org_name,
                has_data=True,
                last_ingested_at=data.get("last_ingested_at"),
                filename=data.get("filename"),
                quality_summary=DataQualitySummary(**data["quality_summary"]),
            )
        except Exception:
            return IngestionStatusResponse(
                tenant_id=self.tenant_id,
                organization_name=self.org_name,
                has_data=False,
            )

    def validate_and_ingest_csv(
        self, file_bytes: bytes, filename: str
    ) -> IngestionUploadResponse:
        """Validate uploaded CSV content, isolate storage, and compute analytical marts."""
        if len(file_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty. Please provide a valid CSV dataset.",
            )

        if len(file_bytes) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {MAX_UPLOAD_BYTES // (1024 * 1024)}MB.",
            )

        try:
            content_str = file_bytes.decode("utf-8-sig")  # handles BOM if present
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file encoding. File must be valid UTF-8 text.",
            ) from None

        reader = csv.DictReader(io.StringIO(content_str))
        if not reader.fieldnames:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV header is missing or unreadable.",
            )

        # Normalize field names
        field_map = {col.strip().lower(): col for col in reader.fieldnames}
        required_fields = ["user_id", "event_name", "event_timestamp"]
        missing = [f for f in required_fields if f not in field_map]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Missing required CSV column(s): {', '.join(missing)}. "
                    f"Required schema: user_id, event_name, event_timestamp "
                    f"(optional: acquisition_channel, plan_type)."
                ),
            )

        user_col = field_map["user_id"]
        event_col = field_map["event_name"]
        ts_col = field_map["event_timestamp"]
        channel_col = field_map.get("acquisition_channel")

        total_rows = 0
        accepted_rows: list[dict[str, Any]] = []
        user_channels: dict[str, str] = {}
        user_signups: dict[str, datetime] = {}
        seen_events: set[tuple[str, str, str]] = set()

        rejection_reasons: dict[str, int] = {}
        rejection_samples: list[str] = []
        duplicate_count = 0

        now_utc = datetime.now(UTC)

        for row_idx, row in enumerate(reader, start=2):
            total_rows += 1
            if total_rows > MAX_ROW_COUNT:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File exceeds row limit of {MAX_ROW_COUNT:,} rows.",
                )

            uid = (row.get(user_col) or "").strip()
            raw_event = (row.get(event_col) or "").strip().lower()
            raw_ts = (row.get(ts_col) or "").strip()

            # 1. Null check on required fields
            if not uid:
                rejection_reasons["missing_user_id"] = rejection_reasons.get("missing_user_id", 0) + 1
                if len(rejection_samples) < 5:
                    rejection_samples.append(f"Row {row_idx}: user_id is missing or blank")
                continue

            if not raw_event:
                rejection_reasons["missing_event_name"] = rejection_reasons.get("missing_event_name", 0) + 1
                if len(rejection_samples) < 5:
                    rejection_samples.append(f"Row {row_idx}: event_name is missing or blank")
                continue

            if not raw_ts:
                rejection_reasons["missing_timestamp"] = rejection_reasons.get("missing_timestamp", 0) + 1
                if len(rejection_samples) < 5:
                    rejection_samples.append(f"Row {row_idx}: event_timestamp is missing or blank")
                continue

            # 2. Canonical event name normalization
            canonical_event = CANONICAL_EVENTS.get(raw_event)
            if not canonical_event:
                rejection_reasons["unsupported_event_name"] = rejection_reasons.get("unsupported_event_name", 0) + 1
                if len(rejection_samples) < 5:
                    rejection_samples.append(
                        f"Row {row_idx}: unsupported event '{raw_event}'. Supported: {', '.join(sorted(set(CANONICAL_EVENTS.values())))}"
                    )
                continue

            # 3. Timestamp parsing & range checks
            try:
                # Handle space or 'T' separator, optional Z or timezone offset
                clean_ts_str = raw_ts.replace("Z", "+00:00")
                parsed_dt = datetime.fromisoformat(clean_ts_str)
                if parsed_dt.tzinfo is None:
                    parsed_dt = parsed_dt.replace(tzinfo=UTC)
            except Exception:
                rejection_reasons["invalid_timestamp_format"] = (
                    rejection_reasons.get("invalid_timestamp_format", 0) + 1
                )
                if len(rejection_samples) < 5:
                    rejection_samples.append(f"Row {row_idx}: invalid timestamp format '{raw_ts}'")
                continue

            if parsed_dt.year < MIN_VALID_YEAR:
                rejection_reasons["prehistoric_timestamp"] = (
                    rejection_reasons.get("prehistoric_timestamp", 0) + 1
                )
                if len(rejection_samples) < 5:
                    rejection_samples.append(f"Row {row_idx}: timestamp earlier than {MIN_VALID_YEAR}")
                continue

            # Future tolerance: max 1 day ahead to accommodate clock skew
            if (parsed_dt - now_utc).total_seconds() > 86400:
                rejection_reasons["future_timestamp"] = (
                    rejection_reasons.get("future_timestamp", 0) + 1
                )
                if len(rejection_samples) < 5:
                    rejection_samples.append(f"Row {row_idx}: timestamp in the future")
                continue

            # 4. Duplicate event check
            dedup_key = (uid, canonical_event, parsed_dt.isoformat())
            if dedup_key in seen_events:
                duplicate_count += 1
                continue
            seen_events.add(dedup_key)

            # 5. Acquisition channel tracking
            raw_channel = (row.get(channel_col) or "").strip() if channel_col else ""
            if raw_channel and uid not in user_channels:
                user_channels[uid] = raw_channel

            # 6. User signup date tracking
            if uid not in user_signups or parsed_dt < user_signups[uid]:
                user_signups[uid] = parsed_dt

            accepted_rows.append({
                "user_id": uid,
                "event_name": canonical_event,
                "event_timestamp": parsed_dt.strftime("%Y-%m-%d %H:%M:%S"),
            })

        rejected_count = sum(rejection_reasons.values())

        if not accepted_rows:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "ValidationFailed",
                    "message": "All rows in the uploaded file were invalid or malformed.",
                    "total_rows": total_rows,
                    "rejection_reasons": rejection_reasons,
                    "rejection_samples": rejection_samples,
                },
            )

        # Compute observation window metrics
        timestamps = [datetime.strptime(r["event_timestamp"], "%Y-%m-%d %H:%M:%S") for r in accepted_rows]
        min_ts = min(timestamps)
        max_ts = max(timestamps)
        coverage_days = (max_ts.date() - min_ts.date()).days + 1

        warnings: list[str] = []
        is_window_complete = coverage_days >= 14
        if not is_window_complete:
            warnings.append(
                f"Observation window spans {coverage_days} day(s) (<14 days). "
                "Funnel conversion rates may be incomplete or volatile."
            )

        if rejected_count > 0:
            warnings.append(f"{rejected_count} row(s) were rejected due to validation errors.")

        if duplicate_count > 0:
            warnings.append(f"{duplicate_count} duplicate event(s) were identified and excluded.")

        # Persist tenant-isolated raw parquet datasets
        self.tenant_raw_dir.mkdir(parents=True, exist_ok=True)
        self.tenant_processed_dir.mkdir(parents=True, exist_ok=True)

        events_df = pd.DataFrame(accepted_rows)
        raw_events_path = self.tenant_raw_dir / "fact_events.parquet"
        events_df.to_parquet(raw_events_path, index=False)

        # Build dim_users DataFrame
        users_records = []
        for uid, signup_dt in user_signups.items():
            users_records.append({
                "user_id": uid,
                "signup_date": signup_dt.strftime("%Y-%m-%d"),
                "acquisition_channel": user_channels.get(uid, "Direct"),
            })
        users_df = pd.DataFrame(users_records)
        raw_users_path = self.tenant_raw_dir / "dim_users.parquet"
        users_df.to_parquet(raw_users_path, index=False)

        # Compute and persist mart_funnel.parquet via DuckDB
        mart_funnel_path = self.tenant_processed_dir / "mart_funnel.parquet"
        self._compute_and_save_funnel_mart(raw_users_path, raw_events_path, mart_funnel_path)

        quality_summary = DataQualitySummary(
            total_rows=total_rows,
            accepted_rows=len(accepted_rows),
            rejected_rows=rejected_count,
            duplicate_rows=duplicate_count,
            total_unique_users=len(users_records),
            date_range_start=min_ts.strftime("%Y-%m-%d %H:%M:%S"),
            date_range_end=max_ts.strftime("%Y-%m-%d %H:%M:%S"),
            coverage_days=coverage_days,
            is_window_complete=is_window_complete,
            warnings=warnings,
            rejection_reasons=rejection_reasons,
            rejection_samples=rejection_samples,
        )

        # Save status file for persistence across server restarts
        status_payload = {
            "last_ingested_at": now_utc.isoformat(),
            "filename": Path(filename).name,
            "quality_summary": quality_summary.model_dump(),
        }
        with open(self.status_file, "w", encoding="utf-8") as f:
            json.dump(status_payload, f, indent=2)

        return IngestionUploadResponse(
            status="warning" if warnings else "success",
            message=(
                f"Successfully ingested {len(accepted_rows):,} events across {len(users_records):,} accounts."
            ),
            tenant_id=self.tenant_id,
            quality_summary=quality_summary,
        )

    def _compute_and_save_funnel_mart(
        self, raw_users_path: Path, raw_events_path: Path, mart_funnel_path: Path
    ) -> None:
        """Run DuckDB SQL transformation to generate standard mart_funnel.parquet."""
        u_path = raw_users_path.as_posix()
        e_path = raw_events_path.as_posix()
        m_path = mart_funnel_path.as_posix()

        query = f"""
        COPY (
            WITH user_steps AS (
                SELECT
                    u.user_id,
                    u.acquisition_channel,
                    MAX(CASE WHEN e.event_name = 'signup'            THEN 1 ELSE 0 END) AS reached_signup,
                    MAX(CASE WHEN e.event_name = 'workspace_created' THEN 1 ELSE 0 END) AS reached_workspace,
                    MAX(CASE WHEN e.event_name = 'invite_sent'       THEN 1 ELSE 0 END) AS reached_invite,
                    MAX(CASE WHEN e.event_name = 'first_project'     THEN 1 ELSE 0 END) AS reached_project,
                    MAX(CASE WHEN e.event_name = 'paid'              THEN 1 ELSE 0 END) AS reached_paid
                FROM read_parquet('{u_path}') u
                LEFT JOIN read_parquet('{e_path}') e ON u.user_id = e.user_id
                GROUP BY u.user_id, u.acquisition_channel
            )
            SELECT
                acquisition_channel,
                COUNT(*)                                                            AS total_users,
                SUM(reached_signup)                                                 AS signup_users,
                SUM(reached_workspace)                                              AS workspace_users,
                SUM(reached_invite)                                                 AS invite_users,
                SUM(reached_project)                                                AS project_users,
                SUM(reached_paid)                                                   AS paid_users,
                ROUND(SUM(reached_workspace)  * 1.0 / NULLIF(COUNT(*), 0), 4)         AS signup_to_workspace_rate,
                ROUND(SUM(reached_invite)     * 1.0 / NULLIF(SUM(reached_workspace), 0), 4) AS workspace_to_invite_rate,
                ROUND(SUM(reached_project)    * 1.0 / NULLIF(SUM(reached_invite), 0), 4)    AS invite_to_project_rate,
                ROUND(SUM(reached_paid)       * 1.0 / NULLIF(SUM(reached_project), 0), 4)   AS project_to_paid_rate,
                ROUND(SUM(reached_paid)       * 1.0 / NULLIF(COUNT(*), 0), 4)         AS overall_conversion_rate
            FROM user_steps
            GROUP BY ROLLUP(acquisition_channel)
        ) TO '{m_path}' (FORMAT PARQUET);
        """
        con = duckdb.connect()
        try:
            con.execute(query)
        finally:
            con.close()
