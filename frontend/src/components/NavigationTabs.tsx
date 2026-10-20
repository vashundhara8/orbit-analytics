import React from 'react';
import { Filter, Users, FlaskConical } from 'lucide-react';

export type WorkspaceTab = 'funnel' | 'cohorts' | 'experiments';

interface NavigationTabsProps {
  activeTab: WorkspaceTab;
  onTabChange: (tab: WorkspaceTab) => void;
}

export const NavigationTabs: React.FC<NavigationTabsProps> = ({ activeTab, onTabChange }) => {
  const tabs: { id: WorkspaceTab; label: string; icon: React.ReactNode; badge?: string }[] = [
    {
      id: 'funnel',
      label: 'Funnel Intelligence',
      icon: <Filter size={16} />,
    },
    {
      id: 'cohorts',
      label: 'Cohort Retention',
      icon: <Users size={16} />,
    },
    {
      id: 'experiments',
      label: 'Experimentation Lab',
      icon: <FlaskConical size={16} />,
      badge: 'Z-Test & SRM',
    },
  ];

  return (
    <div className="nav-tabs-container">
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            type="button"
            className={`nav-tab-btn ${isActive ? 'nav-tab-active' : ''}`}
            onClick={() => onTabChange(tab.id)}
          >
            {tab.icon}
            <span>{tab.label}</span>
            {tab.badge && <span className="tab-badge">{tab.badge}</span>}
          </button>
        );
      })}
    </div>
  );
};
