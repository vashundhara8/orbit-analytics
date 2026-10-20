CREATE OR REPLACE TABLE mart_experiment_results AS
WITH experiment_activation AS (
    SELECT
        ex.user_id,
        ex.experiment_name,
        ex.variant,
        CASE
            WHEN EXISTS (
                SELECT 1
                FROM stg_events e
                WHERE e.user_id = ex.user_id
                  AND e.event_name = 'workspace_created'
                  AND e.event_ts >= ex.assigned_ts
                  AND e.event_ts <= ex.assigned_ts + INTERVAL 7 DAY
            ) THEN 1
            ELSE 0
        END AS activated
    FROM stg_experiments ex
)

SELECT
    experiment_name,
    variant,
    COUNT(*)            AS users,
    SUM(activated)      AS activated_users,
    ROUND(SUM(activated) * 1.0 / COUNT(*), 4) AS activation_rate
FROM experiment_activation
GROUP BY experiment_name, variant
ORDER BY experiment_name, variant;
