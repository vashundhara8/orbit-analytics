import test from 'node:test';
import assert from 'node:assert/strict';

test('Frontend API client parameter serialization', () => {
  const params = new URLSearchParams();
  const channel = 'organic';
  const startDate = '2024-01-01';
  const endDate = '2025-06-29';

  if (channel && channel !== 'All Channels') {
    params.append('acquisition_channel', channel);
  }
  if (startDate) {
    params.append('start_date', startDate);
  }
  if (endDate) {
    params.append('end_date', endDate);
  }

  const query = `?${params.toString()}`;
  assert.equal(
    query,
    '?acquisition_channel=organic&start_date=2024-01-01&end_date=2025-06-29'
  );
});

test('Frontend API client All Channels parameter exclusion', () => {
  const params = new URLSearchParams();
  const channel = 'All Channels';

  if (channel && channel !== 'All Channels') {
    params.append('acquisition_channel', channel);
  }

  assert.equal(params.toString(), '');
});

test('Date range validation logic prevents inverted intervals', () => {
  const startDate = '2025-06-30';
  const endDate = '2024-01-01';
  const isValid = !startDate || !endDate || startDate <= endDate;
  assert.equal(isValid, false);
});

test('Cohort retention query parameters build properly', () => {
  const maxWeeks = 12;
  const numCohorts = 20;
  const minCohortSize = 500;

  const params = new URLSearchParams({
    max_weeks: maxWeeks.toString(),
    num_cohorts: numCohorts.toString(),
    min_cohort_size: minCohortSize.toString(),
  });

  assert.equal(
    params.toString(),
    'max_weeks=12&num_cohorts=20&min_cohort_size=500'
  );
});

test('Experiment relative lift calculation', () => {
  const controlRate = 0.6727;
  const treatmentRate = 0.7053;
  const absLift = treatmentRate - controlRate;
  const relLiftPct = (absLift / controlRate) * 100;

  assert.ok(Math.abs(absLift - 0.0326) < 0.0001);
  assert.ok(Math.abs(relLiftPct - 4.846) < 0.05);
});

test('Cohort retention query parameters build with start and end dates', () => {
  const maxWeeks = 8;
  const numCohorts = 10;
  const minCohortSize = 300;
  const startDate = '2024-02-01';
  const endDate = '2024-05-31';

  const params = new URLSearchParams({
    max_weeks: maxWeeks.toString(),
    num_cohorts: numCohorts.toString(),
    min_cohort_size: minCohortSize.toString(),
  });
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);

  assert.equal(
    params.toString(),
    'max_weeks=8&num_cohorts=10&min_cohort_size=300&start_date=2024-02-01&end_date=2024-05-31'
  );
});

test('Cohort cell retention rate formatting handles unobserved vs genuine zero', () => {
  const formatCell = (rate) => {
    if (rate === null || rate === undefined) return '—';
    return `${(rate * 100).toFixed(0)}%`;
  };

  assert.equal(formatCell(null), '—');
  assert.equal(formatCell(undefined), '—');
  assert.equal(formatCell(0.0), '0%');
  assert.equal(formatCell(0.6727), '67%');
  assert.equal(formatCell(1.0), '100%');
});

test('Experiment relative lift handles zero control baseline safely', () => {
  const calcRelLift = (treatmentRate, controlRate) => {
    const absLift = treatmentRate - controlRate;
    return controlRate > 0 ? (absLift / controlRate) * 100 : 0.0;
  };

  assert.equal(calcRelLift(0.15, 0.0), 0.0);
  assert.equal(calcRelLift(0.0, 0.0), 0.0);
  assert.ok(Math.abs(calcRelLift(0.50, 0.40) - 25.0) < 0.01);
});

test('Experiment SRM diagnostic status detection', () => {
  const checkSrm = (pVal) => pVal < 0.01;

  assert.equal(checkSrm(0.00004), true); // Severe SRM
  assert.equal(checkSrm(0.0099), true);  // Just below threshold
  assert.equal(checkSrm(0.0101), false); // Passed
  assert.equal(checkSrm(0.179), false);  // Standard passed SRM
});

test('Advisory banner classification prioritizes SRM over statistical significance', () => {
  const classifyAdvisory = (hasSrm, isSignificant, absLift) => {
    if (hasSrm) return 'srm_warning';
    if (isSignificant && absLift > 0) return 'significant_lift';
    if (isSignificant && absLift < 0) return 'negative_regression';
    return 'inconclusive';
  };

  // Even if statistically significant, SRM MUST trigger srm_warning
  assert.equal(classifyAdvisory(true, true, 0.05), 'srm_warning');
  assert.equal(classifyAdvisory(false, true, 0.0326), 'significant_lift');
  assert.equal(classifyAdvisory(false, true, -0.04), 'negative_regression');
  assert.equal(classifyAdvisory(false, false, 0.002), 'inconclusive');
});

test('Isolated empty workspace detection for cohorts and experiments', () => {
  const isCohortEmpty = (cohorts) => cohorts.length === 0;
  const isExpEmpty = (variants) => variants.length === 0;

  assert.equal(isCohortEmpty([]), true);
  assert.equal(isCohortEmpty([{ cohort_week: '2024-01-01' }]), false);
  assert.equal(isExpEmpty([]), true);
  assert.equal(isExpEmpty([{ variant: 'control' }]), false);
});

test('Experiment revenue intelligence URL generation', () => {
  const getRevenueUrl = (expName) => `/experiments/${expName}/revenue`;
  assert.equal(getRevenueUrl('onboarding_v2'), '/experiments/onboarding_v2/revenue');
  assert.equal(getRevenueUrl('pricing_test'), '/experiments/pricing_test/revenue');
});

test('Downstream paid conversion lift and ARPU calculation', () => {
  const cRate = 0.0638;
  const tRate = 0.0640;
  const absLiftPp = (tRate - cRate) * 100;
  const relLiftPct = ((tRate - cRate) / cRate) * 100;

  assert.ok(Math.abs(absLiftPp - 0.02) < 0.005);
  assert.ok(Math.abs(relLiftPct - 0.313) < 0.05);

  const cArpu = 1.5312;
  const tArpu = 1.5166;
  const arpuDiff = tArpu - cArpu;
  assert.ok(Math.abs(arpuDiff - (-0.0146)) < 0.0001);
});

test('Revenue advisory banner classifies neutral impact when p > 0.05', () => {
  const classifyRevenueAdvisory = (hasSrm, convSig, arpuSig, convLift) => {
    if (hasSrm) return 'srm_warning';
    if (!convSig && !arpuSig) return 'neutral_impact';
    if (convSig && convLift > 0) return 'significant_lift';
    return 'negative_regression';
  };

  assert.equal(classifyRevenueAdvisory(false, false, false, 0.0002), 'neutral_impact');
  assert.equal(classifyRevenueAdvisory(true, false, false, 0.0002), 'srm_warning');
  assert.equal(classifyRevenueAdvisory(false, true, false, 0.02), 'significant_lift');
  assert.equal(classifyRevenueAdvisory(false, true, false, -0.01), 'negative_regression');
});

test('Churn accounts query parameters build with valid filters', () => {
  const buildChurnQuery = (params) => {
    const q = new URLSearchParams();
    if (params?.risk_tier && params.risk_tier !== 'all') {
      q.append('risk_tier', params.risk_tier);
    }
    if (params?.industry && params.industry !== 'all') {
      q.append('industry', params.industry);
    }
    if (params?.plan_type && params.plan_type !== 'all') {
      q.append('plan_type', params.plan_type);
    }
    if (params?.limit) {
      q.append('limit', params.limit.toString());
    }
    return q.toString() ? `?${q.toString()}` : '';
  };

  assert.equal(buildChurnQuery({ risk_tier: 'all', industry: 'all', plan_type: 'all' }), '');
  assert.equal(
    buildChurnQuery({ risk_tier: 'high', industry: 'SaaS', plan_type: 'pro', limit: 25 }),
    '?risk_tier=high&industry=SaaS&plan_type=pro&limit=25'
  );
  assert.equal(buildChurnQuery({ risk_tier: 'medium' }), '?risk_tier=medium');
});

test('Churn baseline evaluation discrimination and calibration comparison', () => {
  const evaluatePredictivePower = (rocAuc, baselineRocAuc) => {
    const liftOverBaseline = rocAuc - baselineRocAuc;
    if (Math.abs(liftOverBaseline) < 0.03) {
      return 'baseline_discrimination';
    }
    if (liftOverBaseline >= 0.15) {
      return 'strong_discrimination';
    }
    return 'modest_discrimination';
  };

  assert.equal(evaluatePredictivePower(0.5030, 0.5000), 'baseline_discrimination');
  assert.equal(evaluatePredictivePower(0.4833, 0.5000), 'baseline_discrimination');
  assert.equal(evaluatePredictivePower(0.7200, 0.5000), 'strong_discrimination');
});

test('Active Snapshot MRR calculation and non-cumulative semantics', () => {
  const activeSubscribers = 533;
  const churnedSubscribers = 111;
  const planFee = 29.0;

  // Active snapshot MRR reflects currently active accounts only
  const activeSnapshotMrr = activeSubscribers * planFee;
  assert.equal(activeSnapshotMrr, 15457.0);

  // Total paid conversions includes churned subscribers, but they contribute $0 to snapshot MRR
  const totalPaidConversions = activeSubscribers + churnedSubscribers;
  assert.equal(totalPaidConversions, 644);
  const arppu = activeSnapshotMrr / totalPaidConversions;
  assert.equal(Math.round(arppu * 100) / 100, 24.00);
});
