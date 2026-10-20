CREATE OR REPLACE TABLE mart_product_growth_daily AS
WITH date_spine AS (
    SELECT UNNEST(GENERATE_SERIES(
        (SELECT MIN(signup_date) FROM stg_users),
        (SELECT MAX(signup_date) FROM stg_users),
        INTERVAL 1 DAY
    ))::DATE AS metric_date
),

daily_signups AS (
    SELECT signup_date AS metric_date, COUNT(*) AS new_signups
    FROM stg_users
    GROUP BY signup_date
),

daily_activations AS (
    SELECT
        e.event_date AS metric_date,
        COUNT(DISTINCT e.user_id) AS activated_users
    FROM stg_events e
    WHERE e.event_name = 'workspace_created'
    GROUP BY e.event_date
),

daily_conversions AS (
    SELECT
        paid_start_date AS metric_date,
        COUNT(*) AS new_paid
    FROM stg_subscriptions
    WHERE paid_start_date IS NOT NULL
    GROUP BY paid_start_date
),

daily_churns AS (
    SELECT
        cancel_date AS metric_date,
        COUNT(*) AS churned_users
    FROM stg_subscriptions
    WHERE cancel_date IS NOT NULL
    GROUP BY cancel_date
),

cumulative_mrr AS (
    SELECT
        d.metric_date,
        SUM(s.mrr) AS total_mrr
    FROM date_spine d
    CROSS JOIN stg_subscriptions s
    WHERE s.paid_start_date IS NOT NULL
      AND s.paid_start_date <= d.metric_date
      AND (s.cancel_date IS NULL OR s.cancel_date > d.metric_date)
    GROUP BY d.metric_date
),

retention_30d AS (
    SELECT
        u.signup_date AS metric_date,
        COUNT(DISTINCT u.user_id) AS cohort_size,
        COUNT(DISTINCT e.user_id) AS retained_d30
    FROM stg_users u
    LEFT JOIN stg_events e
        ON u.user_id = e.user_id
        AND e.event_date BETWEEN u.signup_date + 28 AND u.signup_date + 32
    GROUP BY u.signup_date
)

SELECT
    d.metric_date,
    COALESCE(ds.new_signups, 0)                                                AS new_signups,
    COALESCE(da.activated_users, 0)                                            AS activated_users,
    ROUND(COALESCE(da.activated_users, 0) * 1.0 / NULLIF(ds.new_signups, 0), 4) AS activation_rate,
    COALESCE(dc.new_paid, 0)                                                   AS new_paid,
    ROUND(COALESCE(dc.new_paid, 0) * 1.0 / NULLIF(ds.new_signups, 0), 4)      AS trial_to_paid_rate,
    CASE
        WHEN d.metric_date + 32 <= (SELECT MAX(event_date) FROM stg_events)
        THEN ROUND(COALESCE(r.retained_d30, 0) * 1.0 / NULLIF(r.cohort_size, 0), 4)
        ELSE NULL
    END                                                                        AS d30_retention_rate,
    COALESCE(dch.churned_users, 0)                                             AS churned_users,
    ROUND(COALESCE(dch.churned_users, 0) * 1.0 / NULLIF(ds.new_signups, 0), 4) AS churn_rate,
    COALESCE(cm.total_mrr, 0)                                                  AS mrr
FROM date_spine d
LEFT JOIN daily_signups ds      ON d.metric_date = ds.metric_date
LEFT JOIN daily_activations da  ON d.metric_date = da.metric_date
LEFT JOIN daily_conversions dc  ON d.metric_date = dc.metric_date
LEFT JOIN daily_churns dch      ON d.metric_date = dch.metric_date
LEFT JOIN cumulative_mrr cm     ON d.metric_date = cm.metric_date
LEFT JOIN retention_30d r       ON d.metric_date = r.metric_date
ORDER BY d.metric_date;
