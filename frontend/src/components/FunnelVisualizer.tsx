import React from 'react';
import { FunnelStageItem } from '../types/api';

interface FunnelVisualizerProps {
  stages: FunnelStageItem[];
  cohortSize: number;
  overallConversionRate: number;
}

const BAR_COLORS = [
  'linear-gradient(90deg, #14B8A6, #0D9488)', // Teal
  'linear-gradient(90deg, #38BDF8, #0284C7)', // Sky
  'linear-gradient(90deg, #84CC16, #65A30D)', // Lime
  'linear-gradient(90deg, #F59E0B, #D97706)', // Amber
  'linear-gradient(90deg, #FB7185, #E11D48)', // Coral
];

export const FunnelVisualizer: React.FC<FunnelVisualizerProps> = ({
  stages,
  cohortSize,
  overallConversionRate,
}) => {
  return (
    <div className="funnel-visual-section">
      <div className="section-header">
        <div>
          <h2 className="section-title">Five-Stage Behavioral Conversion Funnel</h2>
          <p className="section-caption">
            Visualized drop-off progression from account registration through active paid subscription
          </p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Overall Conversion</div>
          <div
            style={{
              fontFamily: 'var(--font-heading)',
              fontSize: '1.4rem',
              fontWeight: 700,
              color: 'var(--accent-teal)',
            }}
          >
            {(overallConversionRate * 100).toFixed(2)}%
          </div>
        </div>
      </div>

      <div className="funnel-bars-container">
        {stages.map((stage, idx) => {
          // Proportionate width based on initial cohort
          const widthPercent =
            cohortSize > 0 ? Math.max((stage.entering_users / cohortSize) * 100, 4) : 0;

          return (
            <div key={stage.step_id} className="funnel-bar-row">
              <div className="funnel-bar-info">
                <span className="funnel-bar-title">
                  {stage.step_order}. {stage.name}
                </span>
                <span className="funnel-bar-desc">{stage.description}</span>
              </div>

              <div className="funnel-bar-track">
                <div
                  className="funnel-bar-fill"
                  style={{
                    width: `${widthPercent}%`,
                    background: BAR_COLORS[idx % BAR_COLORS.length],
                  }}
                >
                  {stage.entering_users.toLocaleString()} users
                </div>
              </div>

              <div className="funnel-bar-stat">
                <span className="funnel-bar-stat-val">
                  {(stage.cumulative_conversion_rate * 100).toFixed(1)}% total
                </span>
                <span className="funnel-bar-stat-rate">
                  {idx === 0
                    ? '100% baseline'
                    : `${(stage.step_conversion_rate * 100).toFixed(1)}% from prev`}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
