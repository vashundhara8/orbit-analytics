import React from 'react';
import { ChannelBenchmarkItem } from '../types/api';

interface ChannelBenchmarkMatrixProps {
  benchmarks: ChannelBenchmarkItem[];
  overallBenchmark: number;
}

export const ChannelBenchmarkMatrix: React.FC<ChannelBenchmarkMatrixProps> = ({
  benchmarks,
  overallBenchmark,
}) => {
  return (
    <div className="data-panel">
      <div className="section-header">
        <div>
          <h3 className="section-title">Channel Benchmarking Matrix</h3>
          <p className="section-caption">Acquisition efficiency relative to the weighted population benchmark</p>
        </div>
      </div>

      <div className="table-container">
        <table className="orbit-table">
          <thead>
            <tr>
              <th>Channel</th>
              <th className="text-right">Signups</th>
              <th className="text-right">Paid Users</th>
              <th className="text-right">Conversion</th>
              <th className="text-right">Variance</th>
            </tr>
          </thead>
          <tbody>
            {benchmarks.map((item) => {
              const variancePp = item.variance_vs_benchmark * 100;
              const isPositive = variancePp >= 0;

              return (
                <tr key={item.channel}>
                  <td style={{ fontWeight: 600 }}>
                    {item.channel.replace('_', ' ').toUpperCase()}
                  </td>
                  <td className="text-right">{item.total_signups.toLocaleString()}</td>
                  <td className="text-right">{item.paid_customers.toLocaleString()}</td>
                  <td className="text-right" style={{ fontWeight: 600 }}>
                    {(item.conversion_rate * 100).toFixed(2)}%
                  </td>
                  <td className="text-right">
                    <span
                      className={`variance-pill ${
                        isPositive ? 'variance-pos' : 'variance-neg'
                      }`}
                    >
                      {isPositive ? `+${variancePp.toFixed(2)}` : variancePp.toFixed(2)} pp
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: '14px', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
        * True weighted population benchmark: <strong>{(overallBenchmark * 100).toFixed(2)}%</strong> (reflects full cohort conversion, not an unweighted average of channels).
      </div>
    </div>
  );
};
