import React, { useState, useEffect, useCallback } from 'react';
import { Users, Info, Calendar, Sliders, Layers } from 'lucide-react';
import { api } from '../api/client';
import { CohortRetentionResponse } from '../types/api';

interface CohortRetentionViewProps {
  tenantId: string;
}

export const CohortRetentionView: React.FC<CohortRetentionViewProps> = ({ tenantId }) => {
  const [data, setData] = useState<CohortRetentionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [maxWeeks, setMaxWeeks] = useState(12);
  const [numCohorts, setNumCohorts] = useState(15);
  const [minSize, setMinSize] = useState(500);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const loadCohorts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      if (startDate && endDate && startDate > endDate) {
        setError('Start date must not be later than end date.');
        setLoading(false);
        return;
      }

      await api.getDemoToken(tenantId);
      const res = await api.getCohorts(
        maxWeeks,
        numCohorts,
        minSize,
        startDate || undefined,
        endDate || undefined
      );
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load cohort retention data.');
    } finally {
      setLoading(false);
    }
  }, [tenantId, maxWeeks, numCohorts, minSize, startDate, endDate]);

  useEffect(() => {
    loadCohorts();
  }, [tenantId, loadCohorts]);

  // Color generator for heatmap cells
  const getCellBg = (rate: number | null) => {
    if (rate === null) return 'rgba(33, 38, 45, 0.4)'; // unobserved
    if (rate === 0) return 'rgba(239, 68, 68, 0.15)'; // genuine zero
    if (rate >= 0.75) return 'rgba(20, 184, 166, 0.75)'; // High Teal
    if (rate >= 0.5) return 'rgba(20, 184, 166, 0.45)'; // Mid Teal
    if (rate >= 0.35) return 'rgba(56, 189, 248, 0.35)'; // Sky
    if (rate >= 0.25) return 'rgba(132, 204, 22, 0.25)'; // Subtle Lime
    return 'rgba(245, 158, 11, 0.2)'; // Amber
  };

  return (
    <div>
      {/* Configuration Controls Bar */}
      <div className="filter-bar">
        <div className="filter-group" style={{ flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="filter-label">
              <Calendar size={14} /> Cohorts:
            </span>
            <select
              className="filter-select"
              value={numCohorts}
              onChange={(e) => setNumCohorts(Number(e.target.value))}
              disabled={loading}
            >
              <option value={10}>Last 10 Weekly Cohorts</option>
              <option value={15}>Last 15 Weekly Cohorts</option>
              <option value={20}>Last 20 Weekly Cohorts</option>
              <option value={30}>Last 30 Weekly Cohorts</option>
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="filter-label">
              <Sliders size={14} /> Horizon:
            </span>
            <select
              className="filter-select"
              value={maxWeeks}
              onChange={(e) => setMaxWeeks(Number(e.target.value))}
              disabled={loading}
            >
              <option value={12}>Weeks 0 - 12 (Quarterly Lifecycle)</option>
              <option value={8}>Weeks 0 - 8 (Mid-Term Engagement)</option>
              <option value={4}>Weeks 0 - 4 (Initial Month)</option>
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="filter-label">Min Size:</span>
            <input
              type="number"
              className="filter-input"
              style={{ width: '90px' }}
              value={minSize}
              onChange={(e) => setMinSize(Math.max(0, Number(e.target.value)))}
              disabled={loading}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="filter-label">From:</span>
            <input
              type="date"
              className="filter-input"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              disabled={loading}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="filter-label">To:</span>
            <input
              type="date"
              className="filter-input"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              disabled={loading}
            />
          </div>
        </div>

        <button
          type="button"
          className="btn-secondary"
          onClick={() => {
            setMaxWeeks(12);
            setNumCohorts(15);
            setMinSize(500);
            setStartDate('');
            setEndDate('');
          }}
          disabled={loading}
        >
          Reset Cohort Defaults
        </button>
      </div>

      {loading && !data && (
        <div className="state-box">
          <div className="spinner" />
          <p style={{ color: 'var(--text-secondary)' }}>Calculating cohort retention matrix...</p>
        </div>
      )}

      {error && (
        <div className="state-box" style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)' }}>
          <p className="error-title">Cohort Analytical Error</p>
          <p className="error-desc">{error}</p>
        </div>
      )}

      {data && !error && (
        <>
          {/* Milestone KPI Cards */}
          <div className="kpi-grid">
            <div className="kpi-card">
              <div className="kpi-card-header">
                <span className="kpi-card-order">MILESTONE 01</span>
                <span className="kpi-card-name">Week 1 Retention</span>
              </div>
              <div className="kpi-card-value">
                {data.milestones.w1_retention_avg !== null
                  ? `${(data.milestones.w1_retention_avg * 100).toFixed(1)}%`
                  : 'N/A'}
              </div>
              <div className="kpi-card-footer">
                <span className="kpi-metric-badge badge-positive">Onboarding Activation</span>
                <span className="kpi-subtext">Visible cohorts mean</span>
              </div>
            </div>

            <div className="kpi-card">
              <div className="kpi-card-header">
                <span className="kpi-card-order">MILESTONE 02</span>
                <span className="kpi-card-name">Week 4 Retention</span>
              </div>
              <div className="kpi-card-value">
                {data.milestones.w4_retention_avg !== null
                  ? `${(data.milestones.w4_retention_avg * 100).toFixed(1)}%`
                  : 'N/A'}
              </div>
              <div className="kpi-card-footer">
                <span className="kpi-metric-badge badge-positive">30-Day Stickiness</span>
                <span className="kpi-subtext">First-month active</span>
              </div>
            </div>

            <div className="kpi-card">
              <div className="kpi-card-header">
                <span className="kpi-card-order">MILESTONE 03</span>
                <span className="kpi-card-name">Week 8 Retention</span>
              </div>
              <div className="kpi-card-value">
                {data.milestones.w8_retention_avg !== null
                  ? `${(data.milestones.w8_retention_avg * 100).toFixed(1)}%`
                  : 'N/A'}
              </div>
              <div className="kpi-card-footer">
                <span className="kpi-metric-badge badge-positive">Mid-Term Base</span>
                <span className="kpi-subtext">Active account core</span>
              </div>
            </div>

            <div className="kpi-card">
              <div className="kpi-card-header">
                <span className="kpi-card-order">MILESTONE 04</span>
                <span className="kpi-card-name">Week 12 Plateau</span>
              </div>
              <div className="kpi-card-value">
                {data.milestones.w12_retention_avg !== null
                  ? `${(data.milestones.w12_retention_avg * 100).toFixed(1)}%`
                  : 'N/A'}
              </div>
              <div className="kpi-card-footer">
                <span className="kpi-metric-badge badge-positive">Mature Lifecycle</span>
                <span className="kpi-subtext">Quarterly retention</span>
              </div>
            </div>
          </div>

          {/* Maturity & Elapsed Period Notice */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '12px 18px',
              backgroundColor: 'rgba(56, 189, 248, 0.08)',
              border: '1px solid rgba(56, 189, 248, 0.2)',
              borderRadius: 'var(--radius-md)',
              marginBottom: '24px',
              fontSize: '0.84rem',
              color: 'var(--text-secondary)',
            }}
          >
            <Info size={16} color="var(--accent-sky)" />
            <span>
              <strong>Retention Maturity Guard:</strong> Unelapsed or immature observation windows are explicitly
              treated as unobserved (<strong>N/A</strong>) rather than misrepresented as zero retention.
              Milestone averages calculate exclusively over matured observation cells.
            </span>
          </div>

          {/* Heatmap Matrix Table */}
          <div className="data-panel" style={{ marginBottom: '28px' }}>
            <div className="section-header">
              <div>
                <h3 className="section-title">Weekly Cohort Retention Matrix</h3>
                <p className="section-caption">
                  Active user retention by weekly signup cohort across elapsed post-signup weeks
                </p>
              </div>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                Showing {data.cohorts.length} cohorts × {data.max_weeks_horizon + 1} weeks
              </div>
            </div>

            {data.cohorts.length === 0 ? (
              <div
                className="state-box"
                style={{
                  background: 'var(--bg-card)',
                  border: '1px dashed var(--border-color)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '48px 24px',
                }}
              >
                {data.tenant_id !== 'org_orbit_demo' ? (
                  <>
                    <Layers size={44} color="var(--accent-teal)" style={{ marginBottom: '14px', opacity: 0.8 }} />
                    <h3 style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: '8px' }}>
                      Isolated Empty Workspace
                    </h3>
                    <p style={{ color: 'var(--text-secondary)', maxWidth: '520px', fontSize: '0.9rem' }}>
                      Workspace <strong>{data.organization_name}</strong> ({data.tenant_id}) has strict tenant isolation enforced.
                      No cohort retention activity recorded in this partition yet.
                    </p>
                  </>
                ) : (
                  <>
                    <Users size={36} color="var(--text-muted)" style={{ marginBottom: '12px' }} />
                    <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '6px' }}>No Matching Cohorts</h3>
                    <p style={{ color: 'var(--text-secondary)' }}>
                      No cohorts found matching the current minimum size filter ({minSize}) or date bounds.
                    </p>
                  </>
                )}
              </div>
            ) : (
              <div className="table-container">
                <table className="orbit-table" style={{ fontSize: '0.8rem' }}>
                  <thead>
                    <tr>
                      <th style={{ minWidth: '110px' }}>Cohort Week</th>
                      <th className="text-right" style={{ minWidth: '85px' }}>Cohort Size</th>
                      {Array.from({ length: data.max_weeks_horizon + 1 }).map((_, idx) => (
                        <th key={idx} className="text-right" style={{ minWidth: '55px' }}>
                          W{idx}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.cohorts.map((cohort) => (
                      <tr key={cohort.cohort_week}>
                        <td style={{ fontWeight: 600, fontFamily: 'monospace' }}>
                          {cohort.cohort_week}
                        </td>
                        <td className="text-right" style={{ color: 'var(--text-secondary)' }}>
                          {cohort.cohort_size.toLocaleString()}
                        </td>
                        {cohort.cells.map((cell) => {
                          const hasRate = cell.retention_rate !== null;
                          return (
                            <td
                              key={cell.weeks_since_signup}
                              className="text-right"
                              style={{
                                backgroundColor: getCellBg(cell.retention_rate),
                                color: hasRate ? '#F0F6FC' : 'var(--text-muted)',
                                fontWeight: hasRate && cell.weeks_since_signup === 0 ? 700 : 500,
                                borderRight: '1px solid rgba(0, 0, 0, 0.2)',
                              }}
                              title={
                                hasRate
                                  ? `${cohort.cohort_week} W${cell.weeks_since_signup}: ${(
                                      cell.retention_rate! * 100
                                    ).toFixed(1)}% (${cell.active_users?.toLocaleString()} active users)`
                                  : `${cohort.cohort_week} W${cell.weeks_since_signup}: Unelapsed / Immature Observation Window`
                              }
                            >
                              {hasRate ? `${(cell.retention_rate! * 100).toFixed(0)}%` : '—'}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
