import React from 'react';
import { ArrowDownRight, ArrowUpRight } from 'lucide-react';
import { FunnelStageItem } from '../types/api';

interface KpiStripProps {
  stages: FunnelStageItem[];
}

export const KpiStrip: React.FC<KpiStripProps> = ({ stages }) => {
  return (
    <div className="kpi-grid">
      {stages.map((stage, idx) => {
        const isFirst = idx === 0;
        const stepRateStr = isFirst ? '100.0%' : `${(stage.step_conversion_rate * 100).toFixed(1)}%`;
        const dropStr = isFirst
          ? 'Cohort Baseline'
          : `-${(stage.drop_off_rate * 100).toFixed(1)}% drop`;

        const isHealthy = isFirst || stage.step_conversion_rate >= 0.65;
        const badgeClass = isFirst
          ? 'badge-positive'
          : isHealthy
          ? 'badge-positive'
          : stage.step_conversion_rate >= 0.5
          ? 'badge-warning'
          : 'badge-danger';

        return (
          <div key={stage.step_id} className="kpi-card">
            <div className="kpi-card-header">
              <span className="kpi-card-order">0{stage.step_order}. STAGE</span>
              <span className="kpi-card-name">{stage.name}</span>
            </div>

            <div className="kpi-card-value">
              {stage.entering_users.toLocaleString()}
            </div>

            <div className="kpi-card-footer">
              <span className={`kpi-metric-badge ${badgeClass}`}>
                {isHealthy ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}
                {stepRateStr}
              </span>
              <span className="kpi-subtext">{dropStr}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
};
