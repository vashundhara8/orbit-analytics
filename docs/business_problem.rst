Business Problem
================

Context
-------

A B2B SaaS company offers a project-management platform with a freemium model.
Users sign up for free, optionally start a 14-day trial of premium features,
and may convert to a paid Pro or Enterprise plan.

The company has **strong top-of-funnel signup volume** but **weak paid
conversion** and rising churn among early-stage accounts.

Questions for Leadership
------------------------

1. **Which users activate?**
   Activation is defined as creating a workspace within 7 days of signup.
   Leadership wants to understand which acquisition channels, company sizes,
   and industries produce the highest activation rates.

2. **Which onboarding steps cause drop-off?**
   The expected user journey is: signup → workspace created → invite sent →
   first project. Each transition has a distinct drop-off rate that varies by
   segment.

3. **Which features predict paid conversion?**
   Users who engage with specific features (collaboration, exports, settings
   customization) may convert at higher rates. Identifying these features
   informs product investment.

4. **Did the new onboarding experiment improve activation?**
   The product team shipped a redesigned onboarding flow (``onboarding_v2``)
   to a random subset of new users. A statistically rigorous A/B test is
   needed to measure whether the treatment lifts activation.

5. **Which accounts are at risk of churning?**
   Among paying customers, some show declining engagement (fewer events,
   longer gaps between sessions). A churn-risk model identifies these
   accounts so customer success can intervene.

Success Criteria
----------------

- A clean, reproducible data pipeline from raw events to analytical marts.
- Quantified funnel drop-offs with actionable segment breakdowns.
- A statistically significant A/B test result with confidence intervals.
- A churn-risk scoring model with clear feature importance.
- An interactive dashboard that a non-technical stakeholder can use.
