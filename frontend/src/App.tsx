import React, { useEffect, useState, useCallback } from 'react';
import { AlertCircle, RefreshCw, Layers } from 'lucide-react';
import { api } from './api/client';
import { FunnelAnalysisResponse } from './types/api';
import { TopNav } from './components/TopNav';
import { NavigationTabs, WorkspaceTab } from './components/NavigationTabs';
import { FilterBar } from './components/FilterBar';
import { KpiStrip } from './components/KpiStrip';
import { FunnelVisualizer } from './components/FunnelVisualizer';
import { StageEfficiencyTable } from './components/StageEfficiencyTable';
import { ChannelBenchmarkMatrix } from './components/ChannelBenchmarkMatrix';
import { CohortRetentionView } from './components/CohortRetentionView';
import { ExperimentationView } from './components/ExperimentationView';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<WorkspaceTab>('funnel');
  const [funnelData, setFunnelData] = useState<FunnelAnalysisResponse | null>(null);
  const [currentTenantId, setCurrentTenantId] = useState('org_orbit_demo');
  const [organizationName, setOrganizationName] = useState('Orbit Reference SaaS Corp');
  const [selectedChannel, setSelectedChannel] = useState('All Channels');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadFunnelData = useCallback(
    async (tenantId: string, channel: string, start: string, end: string) => {
      try {
        setLoading(true);
        setError(null);

        // Ensure token for active tenant
        const authRes = await api.getDemoToken(tenantId);
        setOrganizationName(authRes.user.organization_name);

        const funnelRes = await api.getFunnel(channel, start, end);
        setFunnelData(funnelRes);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to connect to Orbit Analysis API';
        setError(message);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    loadFunnelData(currentTenantId, selectedChannel, startDate, endDate);
  }, [currentTenantId, loadFunnelData]);

  const handleFilterChange = (channel: string, start: string, end: string) => {
    setSelectedChannel(channel);
    setStartDate(start);
    setEndDate(end);
    loadFunnelData(currentTenantId, channel, start, end);
  };

  const handleReset = () => {
    setSelectedChannel('All Channels');
    setStartDate('');
    setEndDate('');
    loadFunnelData(currentTenantId, 'All Channels', '', '');
  };

  const handleTenantSwitch = (newTenantId: string) => {
    setCurrentTenantId(newTenantId);
    setSelectedChannel('All Channels');
    setStartDate('');
    setEndDate('');
  };

  return (
    <div className="app-container">
      <TopNav
        organizationName={organizationName}
        tenantId={currentTenantId}
        userRole="Senior Analyst"
        onTenantSwitch={handleTenantSwitch}
      />

      <NavigationTabs activeTab={activeTab} onTabChange={setActiveTab} />

      {activeTab === 'funnel' && (
        <>
          <header className="page-header">
            <h1 className="page-title">Funnel Intelligence Workspace</h1>
            <p className="page-subtitle">
              End-to-end product conversion analysis powered by FastAPI, DuckDB vectorized analytical marts,
              and cryptographically isolated tenant workspaces.
            </p>
          </header>

          <FilterBar
            availableChannels={funnelData?.available_channels || []}
            selectedChannel={selectedChannel}
            startDate={startDate}
            endDate={endDate}
            onFilterChange={handleFilterChange}
            onReset={handleReset}
            isLoading={loading}
          />

          {loading && !funnelData && (
            <div className="state-box">
              <div className="spinner" />
              <p style={{ color: 'var(--text-secondary)' }}>
                Executing tenant-scoped analytical query on DuckDB engine...
              </p>
            </div>
          )}

          {error && (
            <div className="state-box" style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)' }}>
              <AlertCircle size={40} color="var(--accent-coral)" style={{ marginBottom: '14px' }} />
              <h3 className="error-title">Analytical Query Error</h3>
              <p className="error-desc">{error}</p>
              <button
                className="btn-secondary"
                onClick={() => loadFunnelData(currentTenantId, selectedChannel, startDate, endDate)}
              >
                <RefreshCw size={14} /> Retry Query
              </button>
            </div>
          )}

          {funnelData && !error && (
            <>
              {funnelData.cohort_size === 0 ? (
                <div
                  className="state-box"
                  style={{
                    background: 'var(--bg-card)',
                    border: '1px dashed var(--border-color)',
                    borderRadius: 'var(--radius-lg)',
                    padding: '48px 24px',
                  }}
                >
                  <Layers size={44} color="var(--accent-teal)" style={{ marginBottom: '14px', opacity: 0.8 }} />
                  <h3 style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: '8px' }}>
                    Isolated Empty Workspace
                  </h3>
                  <p style={{ color: 'var(--text-secondary)', maxWidth: '520px', fontSize: '0.9rem' }}>
                    Workspace <strong>{funnelData.organization_name}</strong> ({funnelData.tenant_id}) has strict tenant isolation enforced.
                    No data exists in this tenant partition yet. Switch back to <em>Orbit Reference SaaS Corp</em> to review the 100k user dataset.
                  </p>
                </div>
              ) : (
                <>
                  <KpiStrip stages={funnelData.stages} />

                  <FunnelVisualizer
                    stages={funnelData.stages}
                    cohortSize={funnelData.cohort_size}
                    overallConversionRate={funnelData.overall_conversion_rate}
                  />

                  <div className="split-grid">
                    <StageEfficiencyTable stages={funnelData.stages} />
                    <ChannelBenchmarkMatrix
                      benchmarks={funnelData.channel_benchmarks}
                      overallBenchmark={funnelData.overall_conversion_rate}
                    />
                  </div>
                </>
              )}
            </>
          )}
        </>
      )}

      {activeTab === 'cohorts' && (
        <>
          <header className="page-header">
            <h1 className="page-title">Cohort Retention Intelligence</h1>
            <p className="page-subtitle">
              Weekly customer retention matrices, maturity guards, elapsed-period masking, and milestone benchmarks.
            </p>
          </header>

          <CohortRetentionView tenantId={currentTenantId} />
        </>
      )}

      {activeTab === 'experiments' && (
        <>
          <header className="page-header">
            <h1 className="page-title">Experimentation Lab</h1>
            <p className="page-subtitle">
              A/B testing inference, pooled two-proportion z-tests, Wald confidence intervals, and Sample Ratio Mismatch (SRM) diagnostics.
            </p>
          </header>

          <ExperimentationView tenantId={currentTenantId} />
        </>
      )}
    </div>
  );
};

export default App;
