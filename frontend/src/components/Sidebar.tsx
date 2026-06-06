import {
  LayoutDashboard, Camera, Video, AlertTriangle, Settings, Activity,
} from 'lucide-react';
import type { TabId } from '../types';

interface SidebarProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  alertCount: number;
}

const navItems: { id: TabId; label: string; icon: typeof LayoutDashboard }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'cameras', label: 'Cameras', icon: Camera },
  { id: 'recordings', label: 'Recordings', icon: Video },
  { id: 'alerts', label: 'Alert Rules', icon: AlertTriangle },
];

export default function Sidebar({ activeTab, onTabChange, alertCount }: SidebarProps) {
  return (
    <nav className="sidebar">
      <div className="brand">
        <div className="brand-icon">
          <Activity color="white" size={20} />
        </div>
        <span className="brand-title">LiveDetect</span>
      </div>

      <div className="nav-items">
        {navItems.map((item) => (
          <button
            key={item.id}
            className={`nav-item${activeTab === item.id ? ' active' : ''}`}
            onClick={() => onTabChange(item.id)}
          >
            <item.icon size={20} />
            <span className="nav-label">{item.label}</span>
            {item.id === 'alerts' && alertCount > 0 && (
              <span className="nav-badge">{alertCount}</span>
            )}
          </button>
        ))}

        <div className="nav-spacer" />

        <button
          className={`nav-item${activeTab === 'settings' ? ' active' : ''}`}
          onClick={() => onTabChange('settings')}
        >
          <Settings size={20} />
          <span className="nav-label">Settings</span>
        </button>
      </div>
    </nav>
  );
}
