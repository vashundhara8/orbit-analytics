CREATE OR REPLACE VIEW stg_subscriptions AS
SELECT
    user_id,
    CAST(trial_start_date AS DATE)  AS trial_start_date,
    CAST(paid_start_date AS DATE)   AS paid_start_date,
    CAST(cancel_date AS DATE)       AS cancel_date,
    COALESCE(CAST(mrr AS DOUBLE), 0) AS mrr,
    CASE
        WHEN paid_start_date IS NOT NULL AND cancel_date IS NULL THEN 'active'
        WHEN cancel_date IS NOT NULL                             THEN 'churned'
        WHEN trial_start_date IS NOT NULL                        THEN 'trial'
        ELSE 'free'
    END AS subscription_status
FROM raw_fact_subscriptions
WHERE user_id IS NOT NULL;
