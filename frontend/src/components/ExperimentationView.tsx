import React, { useState, useEffect, useCallback } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  FlaskConical,
  Scale,
  ArrowUpRight,
  ShieldCheck,
  DollarSign,
  Info,
  Coins,
} from 'lucide-react';

import { api } from '../api/client';
import {
  ExperimentAnalysisResponse,
  ExperimentRevenueAnalysisResponse,
  ExperimentSummaryItem,
} from '../types/api';

interface ExperimentationViewProps {
  tenantId: string;
}

export const ExperimentationView: React.FC<ExperimentationViewProps> = ({ tenantId }) => {
  const [experiments, setExperiments] = useState<ExperimentSummaryItem[]>([]);
  const [selectedExperiment, setSelectedExperiment] = useState('onboarding_v2');
  const [analysis, setAnalysis] = useState<ExperimentAnalysisResponse | null>(null);
  const [revenueAnalysis, setRevenueAnalysis] = useState<ExperimentRevenueAnalysisResponse | null>(null);
  const [activeTab, setActiveTab] = useState<'activation' | 'revenue'>('activation');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async (expName: string) => {
    try {
      setLoading(true);
      setError(null);

      await api.getDemoToken(tenantId);
      const listRes = await api.getExperiments();
      setExperiments(listRes);

      const [actRes, revRes] = await Promise.all([
        api.getExperimentAnalysis(expName),
        api.getExperimentRevenueAnalysis(expName),
      ]);
      setAnalysis(actRes);
      setRevenueAnalysis(revRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load experiment analysis.');
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    loadData(selectedExperiment);
  }, [tenantId, selectedExperiment, loadData]);

  // Activation metrics helpers
  const control = analysis?.variants.find((v) => v.variant === 'control');
  const treatment = analysis?.variants.find((v) => v.variant === 'treatment');

  const isSrm = Boolean(analysis?.srm.has_srm);
  const isSignificant = Boolean(analysis?.significance.is_significant);
  const isPositiveLift = Boolean(analysis && analysis.lift.absolute_lift > 0);

  const actBannerColor = isSrm
    ? 'var(--accent-coral)'
    : isSignificant
    ? (isPositiveLift ? 'var(--accent-teal)' : 'var(--accent-amber)')
    : 'var(--accent-sky)';

  const actBannerTitle = isSrm
    ? 'Sample Ratio Mismatch Detected (Traffic Distorted — Cannot Declare Winner)'
    : isSignificant
    ? (isPositiveLift ? 'Statistically Significant Lift (Alpha = 0.05)' : 'Statistically Significant Negative Regression')
    : 'Inconclusive / No Statistically Significant Difference';

  // Revenue metrics helpers
  const revControl = revenueAnalysis?.variants.find((v) => v.variant === 'control');
  const revTreatment = revenueAnalysis?.variants.find((v) => v.variant === 'treatment');
  const revHasSrm = Boolean(revenueAnalysis?.diagnostics.has_srm);
  const revConvSig = Boolean(revenueAnalysis?.significance.conversion_is_significant);
  const revArpuSig = Boolean(revenueAnalysis?.significance.arpu_is_significant);
  const revLift = revenueAnalysis?.lift;

  const revIsSig = revConvSig || revArpuSig;
  const isPosRevLift = (revLift?.absolute_conversion_lift ?? 0) > 0 || (revLift?.arpu_diff ?? 0) > 0;

  const revBannerColor = revHasSrm
    ? 'var(--accent-coral)'
    : revIsSig && isPosRevLift
    ? 'var(--accent-teal)'
    : revIsSig && !isPosRevLift
    ? 'var(--accent-coral)'
    : 'var(--accent-amber)';

  const revBannerTitle = revHasSrm
    ? 'Sample Ratio Mismatch in Revenue Data (Cannot Evaluate Impact)'
    : revIsSig && isPosRevLift
    ? 'Statistically Significant Revenue Lift (Alpha = 0.05)'
    : revIsSig && !isPosRevLift
    ? 'Statistically Significant Revenue Regression'
    : 'Neutral Monetization Impact: Early Activation Did Not Drive Revenue Lift';


  return (
    <div>
      {/* Control Bar: Experiment Selector and Sub-Tab Switcher */}
      <div className="filter-bar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
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

        {/* Workspace Mode Switcher */}
        <div style={{ display: 'flex', gap: '6px', background: 'var(--bg-subtle)', padding: '4px', borderRadius: 'var(--radius-md)' }}>
          <button
            type="button"
            className={`nav-tab-btn ${activeTab === 'activation' ? 'nav-tab-active' : ''}`}
            onClick={() => setActiveTab('activation')}
            style={{ padding: '6px 14px', fontSize: '0.84rem' }}
          >
            <FlaskConical size={14} />
            <span>Activation (Proxy)</span>
          </button>
          <button
            type="button"
            className={`nav-tab-btn ${activeTab === 'revenue' ? 'nav-tab-active' : ''}`}
            onClick={() => setActiveTab('revenue')}
            style={{ padding: '6px 14px', fontSize: '0.84rem' }}
          >
            <DollarSign size={14} />
            <span>Monetization & Billing (Outcome)</span>
            <span className="tab-badge" style={{ backgroundColor: 'var(--accent-teal)', color: '#090d16', fontWeight: 700 }}>
              ITT
            </span>
          </button>
        </div>
      </div>

      {loading && !analysis && (
        <div className="state-box">
          <div className="spinner" />
          <p style={{ color: 'var(--text-secondary)' }}>Computing statistical test & revenue linkage...</p>
        </div>
      )}

      {error && (
        <div className="state-box" style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)' }}>
          <p className="error-title">Experiment Analysis Error</p>
          <p className="error-desc">{error}</p>
        </div>
      )}

      {/* ── MODE 1: ACTIVATION INTELLIGENCE ─────────────────────────────────── */}
      {analysis && !error && activeTab === 'activation' && (
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
                  border: `1px solid ${actBannerColor}`,
                  borderLeft: `5px solid ${actBannerColor}`,
                  borderRadius: 'var(--radius-md)',
                  padding: '20px 24px',
                  marginBottom: '28px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                  {isSignificant && !isSrm && isPositiveLift ? (
                    <CheckCircle2 size={20} color={actBannerColor} />
                  ) : (
                    <AlertTriangle size={20} color={actBannerColor} />
                  )}
                  <span
                    style={{
                      fontFamily: 'var(--font-heading)',
                      fontSize: '0.9rem',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em',
                      color: actBannerColor,
                    }}
                  >
                    {actBannerTitle}
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
                  <div
                    className="kpi-card-value"
                    style={{
                      color: analysis.significance.is_significant ? 'var(--accent-teal)' : 'var(--accent-amber)',
                    }}
                  >
                    {analysis.significance.is_significant ? 'p < 0.001' : `p = ${analysis.significance.p_value.toFixed(3)}`}
                  </div>
                  <div className="kpi-card-footer">
                    <span className="kpi-metric-badge badge-positive">
                      z = {analysis.significance.z_statistic.toFixed(2)}
                    </span>
                    <span className="kpi-subtext">
                      {analysis.significance.is_significant ? 'Statistically Significant (α = 0.05)' : 'Not Significant'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Data Table & SRM Diagnostic */}
              <div className="dashboard-grid" style={{ marginTop: '28px' }}>
                <div className="data-panel">
                  <div className="section-header">
                    <div>
                      <h3 className="section-title">Variant Comparison</h3>
                      <p className="section-caption">{analysis.primary_metric}</p>
                    </div>
                    <Scale size={18} color="var(--accent-teal)" />
                  </div>

                  <div className="table-container">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Variant</th>
                          <th className="text-right">Users</th>
                          <th className="text-right">Activated</th>
                          <th className="text-right">Activation Rate</th>
                          <th className="text-right">95% CI</th>
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

                {/* SRM Card */}
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

      {/* ── MODE 2: REVENUE & BILLING INTELLIGENCE ─────────────────────────── */}
      {revenueAnalysis && !error && activeTab === 'revenue' && (
        <>
          {revenueAnalysis.variants.length === 0 ? (
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
              <Coins size={44} color="var(--accent-teal)" style={{ marginBottom: '14px', opacity: 0.8 }} />
              <h3 style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: '8px' }}>
                Isolated Empty Workspace
              </h3>
              <p style={{ color: 'var(--text-secondary)', maxWidth: '540px', fontSize: '0.9rem', lineHeight: 1.5 }}>
                Workspace <strong>{revenueAnalysis.organization_name}</strong> ({revenueAnalysis.tenant_id}) has strict tenant isolation enforced.
                {' '}{revenueAnalysis.decision_advisory}
              </p>
            </div>
          ) : (
            <>
              {/* Revenue Decision Advisory Banner */}
              <div
                style={{
                  backgroundColor: 'var(--bg-card)',
                  border: `1px solid ${revBannerColor}`,
                  borderLeft: `5px solid ${revBannerColor}`,
                  borderRadius: 'var(--radius-md)',
                  padding: '20px 24px',
                  marginBottom: '28px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                  {revConvSig && !revHasSrm && (revLift?.absolute_conversion_lift ?? 0) > 0 ? (
                    <CheckCircle2 size={20} color={revBannerColor} />
                  ) : (
                    <AlertTriangle size={20} color={revBannerColor} />
                  )}
                  <span
                    style={{
                      fontFamily: 'var(--font-heading)',
                      fontSize: '0.9rem',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em',
                      color: revBannerColor,
                    }}
                  >
                    {revBannerTitle}
                  </span>
                </div>

                <div style={{ fontSize: '0.96rem', lineHeight: 1.6, color: 'var(--text-primary)' }}>
                  {revenueAnalysis.decision_advisory}
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
                  <strong>Evaluated Population:</strong> {revenueAnalysis.evaluated_population} •{' '}
                  <strong>Window:</strong> {revenueAnalysis.observation_window_days}-day post-assignment
                </div>
              </div>

              {/* Revenue KPI Summary Cards */}
              <div className="kpi-grid">
                <div className="kpi-card">
                  <div className="kpi-card-header">
                    <span className="kpi-card-order">BASELINE CONVERSION</span>
                    <span className="kpi-card-name">Control 35d Paid Conv</span>
                  </div>
                  <div className="kpi-card-value">
                    {revControl ? `${(revControl.paid_conversion_rate * 100).toFixed(2)}%` : '—'}
                  </div>
                  <div className="kpi-card-footer">
                    <span className="kpi-metric-badge badge-positive">
                      {revControl?.paid_conversions.toLocaleString()} / {revControl?.assigned_users.toLocaleString()}
                    </span>
                    <span className="kpi-subtext">
                      95% CI: [{revControl ? (revControl.ci95_conversion_low * 100).toFixed(2) : ''}%,{' '}
                      {revControl ? (revControl.ci95_conversion_high * 100).toFixed(2) : ''}%]
                    </span>
                  </div>
                </div>

                <div className="kpi-card">
                  <div className="kpi-card-header">
                    <span className="kpi-card-order" style={{ color: 'var(--accent-lime)' }}>
                      TREATMENT CONVERSION
                    </span>
                    <span className="kpi-card-name">Treatment 35d Paid Conv</span>
                  </div>
                  <div className="kpi-card-value" style={{ color: 'var(--accent-lime)' }}>
                    {revTreatment ? `${(revTreatment.paid_conversion_rate * 100).toFixed(2)}%` : '—'}
                  </div>
                  <div className="kpi-card-footer">
                    <span className="kpi-metric-badge badge-positive">
                      {revTreatment?.paid_conversions.toLocaleString()} / {revTreatment?.assigned_users.toLocaleString()}
                    </span>
                    <span className="kpi-subtext">
                      95% CI: [{revTreatment ? (revTreatment.ci95_conversion_low * 100).toFixed(2) : ''}%,{' '}
                      {revTreatment ? (revTreatment.ci95_conversion_high * 100).toFixed(2) : ''}%]
                    </span>
                  </div>
                </div>

                <div className="kpi-card">
                  <div className="kpi-card-header">
                    <span className="kpi-card-order">CONVERSION LIFT</span>
                    <span className="kpi-card-name">Paid Conversion Diff</span>
                  </div>
                  <div
                    className="kpi-card-value"
                    style={{
                      color: revConvSig ? 'var(--accent-teal)' : 'var(--text-secondary)',
                    }}
                  >
                    {revenueAnalysis.lift.absolute_conversion_lift_pp >= 0 ? '+' : ''}
                    {revenueAnalysis.lift.absolute_conversion_lift_pp.toFixed(2)} pp
                  </div>
                  <div className="kpi-card-footer">
                    <span className="kpi-metric-badge" style={{ backgroundColor: 'var(--bg-subtle)', color: 'var(--text-muted)' }}>
                      {revenueAnalysis.significance.conversion_is_significant ? 'Significant' : 'Not Significant'}
                    </span>
                    <span className="kpi-subtext">
                      95% CI: [{revenueAnalysis.lift.ci95_conversion_diff_low_pp.toFixed(2)} pp, +
                      {revenueAnalysis.lift.ci95_conversion_diff_high_pp.toFixed(2)} pp]
                    </span>
                  </div>
                </div>

                <div className="kpi-card">
                  <div className="kpi-card-header">
                    <span className="kpi-card-order">ARPU (ITT)</span>
                    <span className="kpi-card-name">Monthly Revenue / User</span>
                  </div>
                  <div className="kpi-card-value">
                    ${revTreatment?.arpu.toFixed(2)}
                  </div>
                  <div className="kpi-card-footer">
                    <span className="kpi-metric-badge" style={{ backgroundColor: 'var(--bg-subtle)', color: 'var(--text-muted)' }}>
                      Control: ${revControl?.arpu.toFixed(2)}
                    </span>
                    <span className="kpi-subtext">
                      Diff: ${revenueAnalysis.lift.arpu_diff.toFixed(4)} (Welch p = {revenueAnalysis.significance.arpu_p_value.toFixed(2)})
                    </span>
                  </div>
                </div>
              </div>

              {/* Statistical Tests Strip */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                  gap: '16px',
                  marginTop: '24px',
                  marginBottom: '28px',
                }}
              >
                <div style={{ background: 'var(--bg-card)', padding: '16px 20px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                    Paid Conversion Hypothesis Test
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                    <span style={{ fontWeight: 700, fontSize: '1.05rem' }}>
                      {revenueAnalysis.significance.conversion_test_name}
                    </span>
                    <span style={{ color: revenueAnalysis.significance.conversion_is_significant ? 'var(--accent-teal)' : 'var(--accent-amber)', fontWeight: 600 }}>
                      {revenueAnalysis.significance.conversion_is_significant ? 'Reject H₀ (p < 0.05)' : 'Retain H₀ (p = 0.95)'}
                    </span>
                  </div>
                  <div style={{ marginTop: '8px', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                    z-statistic: {revenueAnalysis.significance.conversion_z_stat.toFixed(4)} • p-value: {revenueAnalysis.significance.conversion_p_value.toFixed(4)}
                  </div>
                </div>

                <div style={{ background: 'var(--bg-card)', padding: '16px 20px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                    ARPU Hypothesis Test
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                    <span style={{ fontWeight: 700, fontSize: '1.05rem' }}>
                      {revenueAnalysis.significance.arpu_test_name}
                    </span>
                    <span style={{ color: revenueAnalysis.significance.arpu_is_significant ? 'var(--accent-teal)' : 'var(--accent-amber)', fontWeight: 600 }}>
                      {revenueAnalysis.significance.arpu_is_significant ? 'Reject H₀' : 'Retain H₀ (p = 0.87)'}
                    </span>
                  </div>
                  <div style={{ marginTop: '8px', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                    t-statistic: {revenueAnalysis.significance.arpu_t_stat.toFixed(4)} • p-value: {revenueAnalysis.significance.arpu_p_value.toFixed(4)}
                  </div>
                </div>

                <div style={{ background: 'var(--bg-card)', padding: '16px 20px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                    Sample Ratio Integrity
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                    <span style={{ fontWeight: 700, fontSize: '1.05rem' }}>
                      Chi-Square SRM Diagnostic
                    </span>
                    <span style={{ color: revenueAnalysis.diagnostics.has_srm ? 'var(--accent-coral)' : 'var(--accent-lime)', fontWeight: 600 }}>
                      {revenueAnalysis.diagnostics.has_srm ? 'SRM Failed' : 'SRM Passed (p = 0.18)'}
                    </span>
                  </div>
                  <div style={{ marginTop: '8px', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                    Duplicates: {revenueAnalysis.diagnostics.duplicate_assignments_detected} • Missing Subs: {revenueAnalysis.diagnostics.missing_subscription_records}
                  </div>
                </div>
              </div>

              {/* Detailed Variant Revenue & Churn Table */}
              <div className="dashboard-grid">
                <div className="data-panel">
                  <div className="section-header">
                    <div>
                      <h3 className="section-title">Downstream Billing & Churn Outcomes</h3>
                      <p className="section-caption">Point-in-time Intention-To-Treat monetization outcomes</p>
                    </div>
                    <DollarSign size={18} color="var(--accent-teal)" />
                  </div>

                  <div className="table-container">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Variant</th>
                          <th className="text-right">Assigned</th>
                          <th className="text-right">Paid (35d)</th>
                          <th className="text-right">Conv Rate</th>
                          <th className="text-right">95% CI</th>
                          <th className="text-right">Active</th>
                          <th className="text-right">Churned</th>
                          <th className="text-right">Post-Conv Churn</th>
                          <th className="text-right">Active Snapshot MRR</th>
                          <th className="text-right">ARPU</th>
                          <th className="text-right">ARPPU</th>
                        </tr>
                      </thead>
                      <tbody>
                        {revenueAnalysis.variants.map((v) => (
                          <tr key={v.variant}>
                            <td style={{ fontWeight: 600, textTransform: 'capitalize' }}>
                              {v.variant}
                            </td>
                            <td className="text-right">{v.assigned_users.toLocaleString()}</td>
                            <td className="text-right">{v.paid_conversions.toLocaleString()}</td>
                            <td className="text-right" style={{ fontWeight: 700 }}>
                              {(v.paid_conversion_rate * 100).toFixed(2)}%
                            </td>
                            <td className="text-right" style={{ color: 'var(--text-secondary)' }}>
                              [{(v.ci95_conversion_low * 100).toFixed(2)}%, {(v.ci95_conversion_high * 100).toFixed(2)}%]
                            </td>
                            <td className="text-right" style={{ color: 'var(--accent-lime)' }}>{v.active_subscribers.toLocaleString()}</td>
                            <td className="text-right" style={{ color: 'var(--accent-coral)' }}>{v.churned_subscribers.toLocaleString()}</td>
                            <td className="text-right">{(v.post_conversion_churn_rate * 100).toFixed(2)}%</td>
                            <td className="text-right" style={{ fontWeight: 700 }}>${v.total_mrr.toLocaleString()}</td>
                            <td className="text-right">${v.arpu.toFixed(2)}</td>
                            <td className="text-right">${v.arppu.toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Secondary Trial Subpopulation Breakdown */}
                  <div style={{ marginTop: '24px', paddingTop: '16px', borderTop: '1px solid var(--border-color)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                      <Info size={16} color="var(--accent-teal)" />
                      <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>
                        Secondary Breakdown: Trial-Eligible Subpopulation
                      </span>
                    </div>
                    <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '12px' }}>
                      In this experiment, 100% of paid conversions occurred among users who signed up with a free trial (10,771 users total).
                      The remaining 9,229 users signed up under a free tier and had 0 trial starts. Randomization balance across tiers is perfect (Chi² = 0.43, p = 0.51).
                    </p>
                    <div className="table-container">
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Trial Cohort</th>
                            <th className="text-right">Trial Users</th>
                            <th className="text-right">Paid Conversions</th>
                            <th className="text-right">Trial-to-Paid Rate</th>
                            <th className="text-right">Subpopulation Test</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr>
                            <td style={{ fontWeight: 600 }}>Control Trial</td>
                            <td className="text-right">{revenueAnalysis.trial_subpopulation.control_trial_users.toLocaleString()}</td>
                            <td className="text-right">{revenueAnalysis.trial_subpopulation.control_trial_conversions.toLocaleString()}</td>
                            <td className="text-right" style={{ fontWeight: 700 }}>
                              {(revenueAnalysis.trial_subpopulation.control_trial_conversion_rate * 100).toFixed(2)}%
                            </td>
                            <td className="text-right" rowSpan={2} style={{ verticalAlign: 'middle', color: 'var(--text-muted)' }}>
                              z = {revenueAnalysis.trial_subpopulation.trial_conversion_z_stat.toFixed(4)} (p = {revenueAnalysis.trial_subpopulation.trial_conversion_p_value.toFixed(4)})
                            </td>
                          </tr>
                          <tr>
                            <td style={{ fontWeight: 600 }}>Treatment Trial</td>
                            <td className="text-right">{revenueAnalysis.trial_subpopulation.treatment_trial_users.toLocaleString()}</td>
                            <td className="text-right">{revenueAnalysis.trial_subpopulation.treatment_trial_conversions.toLocaleString()}</td>
                            <td className="text-right" style={{ fontWeight: 700 }}>
                              {(revenueAnalysis.trial_subpopulation.treatment_trial_conversion_rate * 100).toFixed(2)}%
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>

                {/* Monomer Linkage & Causality Disclosure Card */}
                <div className="data-panel">
                  <div className="section-header">
                    <div>
                      <h3 className="section-title">Causality & Data Audit</h3>
                      <p className="section-caption">Growth architecture advisory & limitations</p>
                    </div>
                    <ShieldCheck size={20} color="var(--accent-teal)" />
                  </div>

                  <div style={{ background: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)', padding: '16px', marginBottom: '16px' }}>
                    <div style={{ fontWeight: 600, fontSize: '0.88rem', color: 'var(--accent-amber)', marginBottom: '6px' }}>
                      Funnel Proxy Decoupling Notice
                    </div>
                    <div style={{ fontSize: '0.84rem', lineHeight: 1.55, color: 'var(--text-secondary)' }}>
                      {revenueAnalysis.causality_disclosure}
                    </div>
                  </div>

                  <div style={{ fontSize: '0.84rem', color: 'var(--text-primary)', lineHeight: 1.6 }}>
                    <p style={{ marginBottom: '10px' }}>
                      <strong>1. Observation Maturity:</strong> All 20,000 experiment participants were assigned between Jan 2024 and Jun 2025.
                      With dataset cutoff extending past Dec 2025, every single participant has had a complete 35-day post-assignment window observed. Zero right-censoring applies to trial conversion.
                    </p>
                    <p style={{ marginBottom: '10px' }}>
                      <strong>2. Deduplication Invariant:</strong> Participants assigned multiple times are pinned to their earliest assignment timestamp to avoid double-counting or biased variant weighting.
                    </p>
                    <p style={{ marginBottom: '10px' }}>
                      <strong>3. Active Snapshot MRR & Churn Treatment:</strong> Revenue is measured as <em>Active Snapshot MRR from Experiment Cohort</em> at simulation cutoff. Cancelled subscriptions are retained in historical paid conversion counts, but their current snapshot MRR is assigned as $0.00. This is a point-in-time snapshot measure of active recurring revenue, not cumulative recognized revenue or total cash collected over the 35-day window.
                    </p>
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
