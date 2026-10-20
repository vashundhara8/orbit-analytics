CREATE OR REPLACE TABLE mart_cohort_retention AS
WITH cohort_base AS (
    SELECT
        user_id,
        DATE_TRUNC('week', signup_date) AS cohort_week
    FROM stg_users
),

activity AS (
    SELECT DISTINCT
        user_id,
        DATE_TRUNC('week', event_date) AS activity_week
    FROM stg_events
),

cohort_activity AS (
    SELECT
        c.cohort_week,
        a.activity_week,
        DATEDIFF('week', c.cohort_week, a.activity_week) AS weeks_since_signup,
        c.user_id
    FROM cohort_base c
    INNER JOIN activity a ON c.user_id = a.user_id
    WHERE a.activity_week >= c.cohort_week
)

SELECT
    cohort_week,
    weeks_since_signup,
    COUNT(DISTINCT user_id)  AS active_users,
    FIRST(cohort_size)       AS cohort_size,
    ROUND(COUNT(DISTINCT user_id) * 1.0 / FIRST(cohort_size), 4) AS retention_rate
FROM cohort_activity
INNER JOIN (
    SELECT cohort_week AS cw, COUNT(DISTINCT user_id) AS cohort_size
    FROM cohort_base
    GROUP BY cohort_week
) sizes ON cohort_activity.cohort_week = sizes.cw
WHERE weeks_since_signup <= 12
GROUP BY cohort_week, weeks_since_signup
ORDER BY cohort_week, weeks_since_signup;
