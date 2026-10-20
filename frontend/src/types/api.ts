export interface FunnelStageItem {
  step_order: number;
  step_id: string;
  name: string;
  description: string;
  entering_users: number;
  step_conversion_rate: number;
  drop_off_rate: number;
  users_lost: number;
  cumulative_conversion_rate: number;
}

export interface ChannelBenchmarkItem {
  channel: string;
  total_signups: number;
  paid_customers: number;
  conversion_rate: number;
  variance_vs_benchmark: number;
}

export interface FunnelFilterApplied {
  acquisition_channel: string | null;
  start_date: string | null;
  end_date: string | null;
}

export interface FunnelAnalysisResponse {
  tenant_id: string;
  organization_name: string;
  filter_applied: FunnelFilterApplied;
  cohort_size: number;
  overall_conversion_rate: number;
  stages: FunnelStageItem[];
  channel_benchmarks: ChannelBenchmarkItem[];
  available_channels: string[];
}

export interface AuthenticatedUser {
  user_id: string;
  email: string;
  tenant_id: string;
  role: 'admin' | 'analyst' | 'viewer';
  organization_name: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: AuthenticatedUser;
}

export interface HealthResponse {
  status: string;
  app_name: string;
  app_version: string;
  environment: string;
  timestamp: string;
  data_engine: string;
  tenancy_mode: string;
}

// ── Cohort Retention Types ──────────────────────────────────────────────────

export interface CohortCellItem {
  weeks_since_signup: number;
  active_users: number | null;
  retention_rate: number | null;
}

export interface CohortRowItem {
  cohort_week: string;
  cohort_size: number;
  cells: CohortCellItem[];
}

export interface CohortMilestones {
  w1_retention_avg: number | null;
  w4_retention_avg: number | null;
  w8_retention_avg: number | null;
  w12_retention_avg: number | null;
}

export interface CohortRetentionResponse {
  tenant_id: string;
  organization_name: string;
  num_cohorts_returned: number;
  max_weeks_horizon: number;
  min_cohort_size_filter: number;
  milestones: CohortMilestones;
  cohorts: CohortRowItem[];
}

// ── Experimentation Types ───────────────────────────────────────────────────

export interface VariantMetrics {
  variant: string;
  users: number;
  activated_users: number;
  activation_rate: number;
  ci95_low: number;
  ci95_high: number;
}

export interface LiftMetrics {
  absolute_lift: number;
  absolute_lift_pp: number;
  relative_lift: number;
  ci95_difference_low_pp: number;
  ci95_difference_high_pp: number;
}

export interface SignificanceTest {
  test_name: string;
  z_statistic: number;
  p_value: number;
  alpha: number;
  is_significant: boolean;
}

export interface SrmDiagnostic {
  expected_split_pct: number;
  control_pct: number;
  treatment_pct: number;
  chi_square_statistic: number;
  degrees_of_freedom: number;
  p_value: number;
  has_srm: boolean;
  interpretation: string;
}

export interface ExperimentSummaryItem {
  experiment_name: string;
  total_users: number;
  variants_count: number;
}

export interface ExperimentAnalysisResponse {
  tenant_id: string;
  organization_name: string;
  experiment_name: string;
  hypothesis: string;
  primary_metric: string;
  observation_window_days: number;
  variants: VariantMetrics[];
  lift: LiftMetrics;
  significance: SignificanceTest;
  srm: SrmDiagnostic;
  decision_advisory: string;
}
