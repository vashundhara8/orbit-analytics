import React from 'react';
import { FunnelStageItem } from '../types/api';

interface StageEfficiencyTableProps {
  stages: FunnelStageItem[];
}

export const StageEfficiencyTable: React.FC<StageEfficiencyTableProps> = ({ stages }) => {
  return (
    <div className="data-panel">
      <div className="section-header">
        <div>
          <h3 className="section-title">Stage Efficiency & Drop-Off Table</h3>
          <p className="section-caption">Numerical stage-by-stage conversion and user leakage breakdown</p>
        </div>
      </div>

      <div className="table-container">
        <table className="orbit-table">
          <thead>
            <tr>
              <th>Stage</th>
              <th>Description</th>
              <th className="text-right">Entering Users</th>
              <th className="text-right">Users Lost</th>
              <th className="text-right">Step Rate</th>
              <th className="text-right">Drop-off Rate</th>
              <th className="text-right">Overall Rate</th>
            </tr>
          </thead>
          <tbody>
            {stages.map((stage, idx) => (
              <tr key={stage.step_id}>
                <td style={{ fontWeight: 600 }}>
                  0{stage.step_order}. {stage.name}
                </td>
                <td style={{ color: 'var(--text-secondary)' }}>{stage.description}</td>
                <td className="text-right" style={{ fontFamily: 'var(--font-heading)', fontWeight: 600 }}>
                  {stage.entering_users.toLocaleString()}
                </td>
                <td
                  className="text-right"
                  style={{ color: stage.users_lost > 0 ? 'var(--accent-coral)' : 'var(--text-muted)' }}
                >
                  {stage.users_lost > 0 ? `-${stage.users_lost.toLocaleString()}` : '—'}
                </td>
                <td className="text-right" style={{ fontWeight: 600 }}>
                  {idx === 0 ? '100.0%' : `${(stage.step_conversion_rate * 100).toFixed(1)}%`}
                </td>
                <td
                  className="text-right"
                  style={{ color: stage.drop_off_rate > 0 ? 'var(--text-secondary)' : 'var(--text-muted)' }}
                >
                  {idx === 0 ? '0.0%' : `${(stage.drop_off_rate * 100).toFixed(1)}%`}
                </td>
                <td
                  className="text-right"
                  style={{ color: 'var(--accent-teal)', fontWeight: 600 }}
                >
                  {(stage.cumulative_conversion_rate * 100).toFixed(2)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
