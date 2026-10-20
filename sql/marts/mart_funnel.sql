CREATE OR REPLACE TABLE mart_funnel AS
WITH user_steps AS (
    SELECT
        u.user_id,
        u.acquisition_channel,
        MAX(CASE WHEN e.event_name = 'signup'            THEN 1 ELSE 0 END) AS reached_signup,
        MAX(CASE WHEN e.event_name = 'workspace_created' THEN 1 ELSE 0 END) AS reached_workspace,
        MAX(CASE WHEN e.event_name = 'invite_sent'       THEN 1 ELSE 0 END) AS reached_invite,
        MAX(CASE WHEN e.event_name = 'first_project'     THEN 1 ELSE 0 END) AS reached_project,
        MAX(CASE WHEN s.paid_start_date IS NOT NULL       THEN 1 ELSE 0 END) AS reached_paid
    FROM stg_users u
    LEFT JOIN stg_events e        ON u.user_id = e.user_id
    LEFT JOIN stg_subscriptions s ON u.user_id = s.user_id
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
    ROUND(SUM(reached_workspace)  * 1.0 / COUNT(*), 4)         AS signup_to_workspace_rate,
    ROUND(SUM(reached_invite)     * 1.0 / NULLIF(SUM(reached_workspace), 0), 4) AS workspace_to_invite_rate,
    ROUND(SUM(reached_project)    * 1.0 / NULLIF(SUM(reached_invite), 0), 4)    AS invite_to_project_rate,
    ROUND(SUM(reached_paid)       * 1.0 / NULLIF(SUM(reached_project), 0), 4)   AS project_to_paid_rate,
    ROUND(SUM(reached_paid)       * 1.0 / COUNT(*), 4)         AS overall_conversion_rate
FROM user_steps
GROUP BY ROLLUP(acquisition_channel);
