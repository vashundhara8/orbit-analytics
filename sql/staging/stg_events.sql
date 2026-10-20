CREATE OR REPLACE VIEW stg_events AS
SELECT
    event_id,
    user_id,
    LOWER(TRIM(event_name))     AS event_name,
    CAST(event_ts AS TIMESTAMP) AS event_ts,
    CAST(event_ts AS DATE)      AS event_date,
    LOWER(TRIM(device))         AS device,
    session_id
FROM raw_fact_events
WHERE user_id IS NOT NULL
  AND event_ts IS NOT NULL;
