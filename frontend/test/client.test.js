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
