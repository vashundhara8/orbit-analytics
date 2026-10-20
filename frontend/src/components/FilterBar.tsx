import React, { useState } from 'react';
import { Filter, Calendar, RotateCcw } from 'lucide-react';

interface FilterBarProps {
  availableChannels: string[];
  selectedChannel: string;
  startDate: string;
  endDate: string;
  onFilterChange: (channel: string, start: string, end: string) => void;
  onReset: () => void;
  isLoading: boolean;
}

export const FilterBar: React.FC<FilterBarProps> = ({
  availableChannels,
  selectedChannel,
  startDate,
  endDate,
  onFilterChange,
  onReset,
  isLoading,
}) => {
  const [channel, setChannel] = useState(selectedChannel);
  const [start, setStart] = useState(startDate);
  const [end, setEnd] = useState(endDate);
  const [dateError, setDateError] = useState<string | null>(null);

  React.useEffect(() => {
    setChannel(selectedChannel);
    setStart(startDate);
    setEnd(endDate);
  }, [selectedChannel, startDate, endDate]);

  const handleApply = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (start && end && start > end) {
      setDateError('Start date cannot be after end date.');
      return;
    }
    setDateError(null);
    onFilterChange(channel, start, end);
  };

  const handleChannelChange = (newChannel: string) => {
    setChannel(newChannel);
    if (!start || !end || start <= end) {
      setDateError(null);
      onFilterChange(newChannel, start, end);
    }
  };

  const handleReset = () => {
    setChannel('All Channels');
    setStart('');
    setEnd('');
    setDateError(null);
    onReset();
  };

  return (
    <form className="filter-bar" onSubmit={handleApply}>
      <div className="filter-group">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="filter-label">
            <Filter size={14} /> Channel:
          </span>
          <select
            className="filter-select"
            value={channel}
            onChange={(e) => handleChannelChange(e.target.value)}
            disabled={isLoading}
          >
            <option value="All Channels">All Channels (Weighted ROLLUP)</option>
            {availableChannels.map((c) => (
              <option key={c} value={c}>
                {c.replace('_', ' ').toUpperCase()}
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="filter-label">
            <Calendar size={14} /> Date Range:
          </span>
          <input
            type="date"
            className="filter-input"
            value={start}
            placeholder="From"
            onChange={(e) => setStart(e.target.value)}
            disabled={isLoading}
          />
          <span style={{ color: 'var(--text-muted)' }}>to</span>
          <input
            type="date"
            className="filter-input"
            value={end}
            placeholder="To"
            onChange={(e) => setEnd(e.target.value)}
            disabled={isLoading}
          />
          <button
            type="submit"
            className="btn-secondary"
            disabled={isLoading}
            style={{ borderColor: 'var(--accent-teal)', color: 'var(--accent-teal)' }}
          >
            Apply Filters
          </button>
        </div>

        {dateError && (
          <span style={{ color: 'var(--accent-coral)', fontSize: '0.8rem', fontWeight: 500 }}>
            {dateError}
          </span>
        )}
      </div>

      <div>
        <button
          type="button"
          className="btn-secondary"
          onClick={handleReset}
          disabled={isLoading}
          title="Reset all filters to full population"
        >
          <RotateCcw size={14} />
          Reset Filters
        </button>
      </div>
    </form>
  );
};
