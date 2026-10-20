CREATE OR REPLACE VIEW stg_experiments AS
SELECT
    user_id,
    LOWER(TRIM(experiment_name))    AS experiment_name,
    LOWER(TRIM(variant))            AS variant,
    CAST(assigned_ts AS TIMESTAMP)  AS assigned_ts,
    CAST(assigned_ts AS DATE)       AS assigned_date
FROM raw_fact_experiments
WHERE user_id IS NOT NULL
  AND variant IS NOT NULL;
