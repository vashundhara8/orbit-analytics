import React, { useState, useEffect, useCallback } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  FlaskConical,
  Scale,
  ArrowUpRight,
  ShieldCheck,
} from 'lucide-react';
import { api } from '../api/client';
import { ExperimentAnalysisResponse, ExperimentSummaryItem } from '../types/api';

interface ExperimentationViewProps {
  tenantId: string;
}

export const ExperimentationView: React.FC<ExperimentationViewProps> = ({ tenantId }) => {
  const [experiments, setExperiments] = useState<ExperimentSummaryItem[]>([]);
  const [selectedExperiment, setSelectedExperiment] = useState('onboarding_v2');
  const [analysis, setAnalysis] = useState<ExperimentAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async (expName: string) => {
    try {
      setLoading(true);
      setError(null);

      await api.getDemoToken(tenantId);
      const listRes = await api.getExperiments();
      setExperiments(listRes);

      const res = await api.getExperimentAnalysis(expName);
      setAnalysis(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load experiment analysis.');
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    loadData(selectedExperiment);
  }, [tenantId, selectedExperiment, loadData]);

  const control = analysis?.variants.find((v) => v.variant === 'control');
  const treatment = analysis?.variants.find((v) => v.variant === 'treatment');

  const isSrm = Boolean(analysis?.srm.has_srm);
  const isSignificant = Boolean(analysis?.significance.is_significant);
  const isPositiveLift = Boolean(analysis && analysis.lift.absolute_lift > 0);

  const bannerColor = isSrm
    ? 'var(--accent-coral)'
    : isSignificant
    ? (isPositiveLift ? 'var(--accent-teal)' : 'var(--accent-amber)')
    : 'var(--accent-sky)';

  const bannerTitle = isSrm
    ? 'Sample Ratio Mismatch Detected (Traffic Distorted — Cannot Declare Winner)'
    : isSignificant
    ? (isPositiveLift ? 'Statistically Significant Lift (Alpha = 0.05)' : 'Statistically Significant Negative Regression')
    : 'Inconclusive / No Statistically Significant Difference';

  return (
    <div>
      {/* Control Bar: Experiment Selector */}
      <div className="filter-bar">
        <div className="filter-group">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="filter-label">
              <FlaskConical size={14} /> Active Experiment:
            </span>
            <select
              className="filter-select"
              value={selectedExperiment}
              onChange={(e) => setSelectedExperiment(e.target.value)}
              disabled={loading}
            >
              {experiments.length > 0 ? (
                experiments.map((exp) => (
                  <option key={exp.experiment_name} value={exp.experiment_name}>
                    {exp.experiment_name} ({exp.total_users.toLocaleString()} users)
                  </option>
                ))
              ) : (
                <option value="onboarding_v2">onboarding_v2 (Default Reference)</option>
              )}
            </select>
          </div>
        </div>

        <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
          Two-Proportion Z-Test • Wald 95% Confidence Interval • Sample Ratio Mismatch (SRM)
        </div>
      </div>

      {loading && !analysis && (
        <div className="state-box">
          <div className="spinner" />
          <p style={{ color: 'var(--text-secondary)' }}>Computing statistical test & SRM diagnostic...</p>
        </div>
      )}

      {error && (
        <div className="state-box" style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)' }}>
          <p className="error-title">Experiment Analysis Error</p>
          <p className="error-desc">{error}</p>
        </div>
      )}

      {analysis && !error && (
        <>
          {analysis.variants.length === 0 ? (
            <div
              className="state-box"
              style={{
                background: 'var(--bg-card)',
                border: '1px dashed var(--border-color)',
                borderRadius: 'var(--radius-lg)',
                padding: '48px 24px',
                marginTop: '16px',
              }}
            >
              <FlaskConical size={44} color="var(--accent-teal)" style={{ marginBottom: '14px', opacity: 0.8 }} />
              <h3 style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: '8px' }}>
                Isolated Empty Workspace
              </h3>
              <p style={{ color: 'var(--text-secondary)', maxWidth: '540px', fontSize: '0.9rem', lineHeight: 1.5 }}>
                Workspace <strong>{analysis.organization_name}</strong> ({analysis.tenant_id}) has strict tenant isolation enforced.
                {' '}{analysis.decision_advisory}
              </p>
            </div>
          ) : (
            <>
              {/* Decision Advisory Banner */}
              <div
                style={{
                  backgroundColor: 'var(--bg-card)',
                  border: `1px solid ${bannerColor}`,
                  borderLeft: `5px solid ${bannerColor}`,
                  borderRadius: 'var(--radius-md)',
                  padding: '20px 24px',
                  marginBottom: '28px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                  {isSignificant && !isSrm && isPositiveLift ? (
                    <CheckCircle2 size={20} color={bannerColor} />
                  ) : (
                    <AlertTriangle size={20} color={bannerColor} />
                  )}
                  <span
                    style={{
                      fontFamily: 'var(--font-heading)',
                      fontSize: '0.9rem',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em',
                      color: bannerColor,
                    }}
                  >
                    {bannerTitle}
                  </span>
                </div>

                <div style={{ fontSize: '0.96rem', lineHeight: 1.6, color: 'var(--text-primary)' }}>
                  {analysis.decision_advisory}
                </div>

                <div
                  style={{
                    marginTop: '14px',
                    paddingTop: '10px',
                    borderTop: '1px solid var(--border-color)',
                    fontSize: '0.8rem',
                    color: 'var(--text-secondary)',
                  }}
                >
                  <strong>Hypothesis:</strong> {analysis.hypothesis}
                </div>
              </div>

              {/* KPI Summary Cards */}
          <div className="kpi-grid">
            <div className="kpi-card">
              <div className="kpi-card-header">
                <span className="kpi-card-order">BASELINE</span>
                <span className="kpi-card-name">Control Activation</span>
              </div>
              <div className="kpi-card-value">
                {control ? `${(control.activation_rate * 100).toFixed(2)}%` : '—'}
              </div>
              <div className="kpi-card-footer">
                <span className="kpi-metric-badge badge-positive">
                  {control?.users.toLocaleString()} users
                </span>
                <span className="kpi-subtext">
                  95% CI: [{control ? (control.ci95_low * 100).toFixed(1) : ''}%,{' '}
                  {control ? (control.ci95_high * 100).toFixed(1) : ''}%]
                </span>
              </div>
            </div>

            <div className="kpi-card">
              <div className="kpi-card-header">
                <span className="kpi-card-order" style={{ color: 'var(--accent-lime)' }}>
                  TREATMENT
                </span>
                <span className="kpi-card-name">Treatment Activation</span>
              </div>
              <div className="kpi-card-value" style={{ color: 'var(--accent-lime)' }}>
                {treatment ? `${(treatment.activation_rate * 100).toFixed(2)}%` : '—'}
              </div>
              <div className="kpi-card-footer">
                <span className="kpi-metric-badge badge-positive">
                  {treatment?.users.toLocaleString()} users
                </span>
                <span className="kpi-subtext">
                  95% CI: [{treatment ? (treatment.ci95_low * 100).toFixed(1) : ''}%,{' '}
                  {treatment ? (treatment.ci95_high * 100).toFixed(1) : ''}%]
                </span>
              </div>
            </div>

            <div className="kpi-card">
              <div className="kpi-card-header">
                <span className="kpi-card-order">ABSOLUTE LIFT</span>
                <span className="kpi-card-name">Difference (Treatment - Control)</span>
              </div>
              <div
                className="kpi-card-value"
                style={{
                  color: analysis.lift.absolute_lift >= 0 ? 'var(--accent-teal)' : 'var(--accent-coral)',
                }}
              >
                {analysis.lift.absolute_lift_pp >= 0 ? '+' : ''}
                {analysis.lift.absolute_lift_pp.toFixed(2)} pp
              </div>
              <div className="kpi-card-footer">
                <span className="kpi-metric-badge badge-positive">
                  <ArrowUpRight size={13} />
                  {(analysis.lift.relative_lift * 100).toFixed(2)}% rel
                </span>
                <span className="kpi-subtext">
                  95% CI: [{analysis.lift.ci95_difference_low_pp >= 0 ? '+' : ''}
                  {analysis.lift.ci95_difference_low_pp.toFixed(2)} pp, +
                  {analysis.lift.ci95_difference_high_pp.toFixed(2)} pp]
                </span>
              </div>
            </div>

            <div className="kpi-card">
              <div className="kpi-card-header">
                <span className="kpi-card-order">SIGNIFICANCE</span>
                <span className="kpi-card-name">Two-Proportion Z-Test</span>
              </div>
              <div className="kpi-card-value">
                {analysis.significance.p_value < 0.001
                  ? 'p < 0.001'
                  : `p = ${analysis.significance.p_value.toFixed(4)}`}
              </div>
              <div className="kpi-card-footer">
                <span className="kpi-metric-badge badge-positive">
                  z = {analysis.significance.z_statistic.toFixed(2)}
                </span>
                <span className="kpi-subtext">Alpha = 0.05</span>
              </div>
            </div>
          </div>

          {/* Statistical Breakdown & Diagnostics Grid */}
          <div className="split-grid">
            {/* Statistical Test Details */}
            <div className="data-panel">
              <div className="section-header">
                <div>
                  <h3 className="section-title">Statistical Test Details</h3>
                  <p className="section-caption">
                    Rigorous two-proportion pooled z-test with Wald unpooled confidence intervals
                  </p>
                </div>
                <Scale size={20} color="var(--accent-teal)" />
              </div>

              <div className="table-container">
                <table className="orbit-table">
                  <thead>
                    <tr>
                      <th>Variant</th>
                      <th className="text-right">Sample (n)</th>
                      <th className="text-right">Activated</th>
                      <th className="text-right">Activation Rate</th>
                      <th className="text-right">95% Confidence Interval</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analysis.variants.map((v) => (
                      <tr key={v.variant}>
                        <td style={{ fontWeight: 600, textTransform: 'capitalize' }}>
                          {v.variant}
                        </td>
                        <td className="text-right">{v.users.toLocaleString()}</td>
                        <td className="text-right">{v.activated_users.toLocaleString()}</td>
                        <td className="text-right" style={{ fontWeight: 700 }}>
                          {(v.activation_rate * 100).toFixed(2)}%
                        </td>
                        <td className="text-right" style={{ color: 'var(--text-secondary)' }}>
                          [{(v.ci95_low * 100).toFixed(2)}%, {(v.ci95_high * 100).toFixed(2)}%]
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div style={{ marginTop: '16px', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                <strong>Confidence Interval for Difference:</strong> The true population lift lies within{' '}
                <strong style={{ color: 'var(--text-primary)' }}>
                  [{analysis.lift.ci95_difference_low_pp >= 0 ? '+' : ''}
                  {analysis.lift.ci95_difference_low_pp.toFixed(2)} pp, +
                  {analysis.lift.ci95_difference_high_pp.toFixed(2)} pp]
                </strong>{' '}
                with 95% confidence. Because the interval strictly excludes 0.00 pp, the observed gain is statistically credible.
              </div>
            </div>

            {/* Sample Ratio Mismatch (SRM) Card */}
            <div className="data-panel">
              <div className="section-header">
                <div>
                  <h3 className="section-title">Sample Ratio Mismatch (SRM)</h3>
                  <p className="section-caption">Integrity diagnostic on variant traffic assignment</p>
                </div>
                <ShieldCheck
                  size={20}
                  color={analysis.srm.has_srm ? 'var(--accent-coral)' : 'var(--accent-lime)'}
                />
              </div>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '12px 16px',
                  backgroundColor: 'var(--bg-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  marginBottom: '16px',
                }}
              >
                <div>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Status:</span>
                  <div
                    style={{
                      fontWeight: 700,
                      color: analysis.srm.has_srm ? 'var(--accent-coral)' : 'var(--accent-lime)',
                    }}
                  >
                    {analysis.srm.has_srm ? '⚠️ SRM Detected (Biased)' : '✓ SRM Check Passed (Valid)'}
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>p-value:</span>
                  <div style={{ fontWeight: 600 }}>{analysis.srm.p_value.toFixed(4)}</div>
                </div>
              </div>

              <div style={{ fontSize: '0.85rem', lineHeight: 1.5, color: 'var(--text-secondary)' }}>
                {analysis.srm.interpretation}
              </div>

              <div style={{ marginTop: '16px', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Observed split: {analysis.srm.control_pct}% Control vs {analysis.srm.treatment_pct}% Treatment
                (Chi-Square statistic = {analysis.srm.chi_square_statistic.toFixed(2)}, df = 1, threshold = 0.01).
              </div>
            </div>
          </div>
            </>
          )}
        </>
      )}
    </div>
  );
};
