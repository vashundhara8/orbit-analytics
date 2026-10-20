CREATE OR REPLACE VIEW stg_users AS
SELECT
    user_id,
    CAST(signup_date AS DATE)           AS signup_date,
    LOWER(TRIM(company_size))           AS company_size,
    TRIM(industry)                      AS industry,
    LOWER(TRIM(acquisition_channel))    AS acquisition_channel,
    LOWER(TRIM(plan_type))              AS plan_type
FROM raw_dim_users
WHERE user_id IS NOT NULL;
