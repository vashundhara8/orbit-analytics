import React from 'react';
import { Layers, ShieldCheck, Building2 } from 'lucide-react';

interface TopNavProps {
  organizationName: string;
  tenantId: string;
  userRole?: string;
  onTenantSwitch?: (tenantId: string) => void;
}

export const TopNav: React.FC<TopNavProps> = ({
  organizationName,
  tenantId,
  userRole = 'Analyst',
  onTenantSwitch,
}) => {
  return (
    <header className="top-nav">
      <div className="brand-section">
        <div className="brand-logo">
          <Layers size={20} />
        </div>
        <div>
          <span className="brand-title">Orbit Analysis</span>
        </div>
        <span className="brand-tag">Multi-Tenant Cloud</span>
      </div>

      <div className="tenant-badge-group">
        {onTenantSwitch && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Workspace:</span>
            <select
              className="filter-select"
              value={tenantId}
              onChange={(e) => onTenantSwitch(e.target.value)}
              style={{ fontSize: '0.82rem', padding: '4px 8px' }}
            >
              <option value="org_orbit_demo">Orbit Reference SaaS Corp (Full Data)</option>
              <option value="org_acme_corp">Acme Technologies Inc. (Isolated Workspace)</option>
              <option value="org_starlight_saas">Starlight Cloud SaaS (Isolated Workspace)</option>
            </select>
          </div>
        )}

        <div className="tenant-badge" title="Tenant Boundary Enforced via Cryptographic JWT Claims">
          <span className="tenant-indicator" />
          <Building2 size={14} color="var(--accent-teal)" />
          <strong style={{ color: 'var(--text-primary)' }}>{organizationName}</strong>
          <span style={{ color: 'var(--text-muted)' }}>({tenantId})</span>
        </div>

        <div className="tenant-badge" style={{ padding: '6px 12px' }}>
          <ShieldCheck size={14} color="var(--accent-lime)" />
          <span style={{ color: 'var(--text-muted)' }}>Role:</span>
          <strong style={{ color: 'var(--text-primary)' }}>{userRole}</strong>
        </div>
      </div>
    </header>
  );
};
