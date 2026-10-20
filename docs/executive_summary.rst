Executive Summary
=================

Overview
--------

This analysis examines 18 months of product data (Jan 2024 – Jun 2025)
spanning 100,000 users and 1.4 million events to identify growth levers for a
B2B SaaS platform.

Key Findings
------------

1. **Funnel bottleneck at invite → first project.**
   While 72% of users create a workspace and 48% send an invite, only 33%
   complete their first project. This 31% drop-off is the single largest
   conversion gap and represents the highest-leverage improvement
   opportunity.

2. **Overall signup-to-paid conversion is 15.7%.**
   This rate varies significantly by acquisition channel. Referral converts
   at the highest rate, suggesting the company should invest more in its
   referral program.

3. **New onboarding experiment lifts activation by 3.2%.**
   The ``onboarding_v2`` treatment produced a statistically significant
   improvement in workspace creation (p < 0.001). The 4.8% relative lift is
   substantial enough to justify a full rollout.

4. **Retention stabilizes around 37% after week 3.**
   Weekly cohort retention drops sharply in weeks 1–2, then plateaus.
   Targeting users in the first two weeks with engagement nudges could
   meaningfully improve long-term retention.

5. **Churn correlates with recency and engagement depth.**
   A logistic regression model finds that ``days_since_last_event`` and
   ``distinct_event_types`` are the strongest predictors of churn. Accounts
   with fewer than 3 distinct event types and more than 60 days of inactivity
   have elevated churn probability.

Recommendations
---------------

.. list-table::
   :header-rows: 1
   :widths: 10 45 45

   * - Priority
     - Action
     - Expected Impact
   * - 1
     - Roll out ``onboarding_v2`` to all new users.
     - +3.2% activation rate (statistically validated).
   * - 2
     - Add guided first-project templates to reduce invite → project
       drop-off.
     - Projected +5–8% improvement in project completion.
   * - 3
     - Trigger engagement emails for users inactive after 7 days.
     - Improve week 1–2 retention before the plateau.
   * - 4
     - Scale the referral program (highest-converting channel).
     - Higher-quality signups with better unit economics.
   * - 5
     - Flag high-churn-risk accounts in CRM for customer success outreach.
     - Reduce monthly churn by proactive intervention.
