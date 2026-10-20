Data Dictionary
===============

Raw Tables
----------

All raw data is generated synthetically and stored as Parquet files in
``data/raw/``.

dim_users
~~~~~~~~~

One row per user (100,000 rows).

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Column
     - Type
     - Description
   * - ``user_id``
     - string
     - Unique user identifier (e.g., ``u_000001``)
   * - ``signup_date``
     - date
     - Date the user registered (2024-01-01 to 2025-06-30)
   * - ``company_size``
     - string
     - startup, smb, mid-market, or enterprise
   * - ``industry``
     - string
     - One of 8 industry categories
   * - ``acquisition_channel``
     - string
     - organic, paid_search, referral, or partner
   * - ``plan_type``
     - string
     - free, trial, pro, or enterprise

fact_events
~~~~~~~~~~~

One row per product event (~1.4M rows).

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Column
     - Type
     - Description
   * - ``event_id``
     - string
     - UUID for the event
   * - ``user_id``
     - string
     - Foreign key to dim_users
   * - ``event_name``
     - string
     - signup, workspace_created, invite_sent, first_project, feature_used, page_view, settings_changed, export
   * - ``event_ts``
     - timestamp
     - When the event occurred
   * - ``device``
     - string
     - desktop, mobile, or tablet
   * - ``session_id``
     - string
     - Groups events within a session

fact_subscriptions
~~~~~~~~~~~~~~~~~~

One row per user (100,000 rows).

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Column
     - Type
     - Description
   * - ``user_id``
     - string
     - Foreign key to dim_users
   * - ``trial_start_date``
     - date
     - Start of trial period (null if no trial)
   * - ``paid_start_date``
     - date
     - Date of paid conversion (null if never converted)
   * - ``cancel_date``
     - date
     - Date of cancellation (null if still active)
   * - ``mrr``
     - float
     - Monthly recurring revenue (0 if free/churned)

fact_experiments
~~~~~~~~~~~~~~~~

One row per experiment assignment (~20,000 rows).

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Column
     - Type
     - Description
   * - ``user_id``
     - string
     - Foreign key to dim_users
   * - ``experiment_name``
     - string
     - Experiment identifier (``onboarding_v2``)
   * - ``variant``
     - string
     - control or treatment
   * - ``assigned_ts``
     - timestamp
     - When the user was assigned to the experiment

Mart Tables
-----------

Built by DuckDB SQL and exported to ``data/processed/``.

- **mart_funnel** — step-by-step conversion rates by acquisition channel
- **mart_cohort_retention** — weekly retention matrix (cohort × weeks since signup)
- **mart_experiment_results** — per-variant activation rates
- **mart_product_growth_daily** — daily KPI rollups (activation, conversion, retention, churn, MRR)
