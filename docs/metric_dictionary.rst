Metric Dictionary
=================

Core KPIs
---------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - KPI
     - Definition
   * - **Signup-to-activation rate**
     - Users who complete the ``workspace_created`` event within 7 days of
       signup, divided by total signups in that period.
   * - **Trial-to-paid conversion**
     - Trial users whose ``paid_start_date`` is not null, divided by total
       trial users.
   * - **D30 retention rate**
     - Users who fire at least one event between day 28 and day 32 after
       signup, divided by the cohort size.
   * - **Churn rate**
     - Paying users whose ``cancel_date`` falls in the period, divided by
       active paying users at the start of the period.
   * - **MRR (Monthly Recurring Revenue)**
     - Sum of ``mrr`` across all users with an active paid subscription
       (``paid_start_date`` is not null and ``cancel_date`` is null or in the
       future).
   * - **Experiment lift**
     - Treatment activation rate minus control activation rate. Statistical
       significance is assessed with a two-proportion z-test at
       α = 0.05.

Funnel Steps
------------

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Step
     - Event Name
     - Conversion Denominator
   * - Signup
     - ``signup``
     - Total users
   * - Workspace Created
     - ``workspace_created``
     - Signup users
   * - Invite Sent
     - ``invite_sent``
     - Workspace users
   * - First Project
     - ``first_project``
     - Invite users
   * - Paid Conversion
     - ``paid_start_date IS NOT NULL``
     - First-project users

SQL Logic
---------

All mart SQL lives in ``sql/marts/``. Key patterns:

- **mart_funnel.sql** uses ``ROLLUP`` to produce both per-channel and
  overall totals in a single query.
- **mart_cohort_retention.sql** uses ``DATE_TRUNC('week', ...)`` for cohort
  bucketing and ``DATEDIFF('week', ...)`` for period calculation.
- **mart_product_growth_daily.sql** joins a date spine against daily
  aggregates for signups, activations, conversions, churns, and cumulative
  MRR.
