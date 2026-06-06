import { Users, Shield, Smile } from 'lucide-react';
import type { TelemetryStats } from '../types';

interface StatsPanelProps {
  stats: TelemetryStats;
}

export default function StatsPanel({ stats }: StatsPanelProps) {
  return (
    <div className="stats-grid animate-slide-in" style={{ animationDelay: '0.1s' }}>
      <div className="glass-card stat-card">
        <div className="stat-header">
          <Users size={16} color="var(--accent-primary)" />
          Total Live Detections
        </div>
        <div className="stat-value">{stats.total_detections ?? 0}</div>
        <div className="stat-trend trend-up">Current Frame</div>
      </div>

      <div className="glass-card stat-card">
        <div className="stat-header">
          <Shield size={16} color="var(--success)" />
          Mask Compliance
        </div>
        <div className="stat-value">{(stats.mask_compliance_pct ?? 0).toFixed(1)}%</div>
        <div className="stat-trend trend-up">Current Frame</div>
      </div>

      <div className="glass-card stat-card">
        <div className="stat-header">
          <Smile size={16} color="var(--warning)" />
          People Detected
        </div>
        <div className="stat-value">{stats.total_people ?? 0}</div>
        <div className="stat-trend trend-down">Current Frame</div>
      </div>
    </div>
  );
}
