import { AlertTriangle, ShieldCheck } from 'lucide-react';
import type { Alert } from '../types';

interface AlertListProps {
  alerts: Alert[];
}

export default function AlertList({ alerts }: AlertListProps) {
  return (
    <div className="glass-panel alerts-panel animate-slide-in" style={{ animationDelay: '0.3s' }}>
      <div className="panel-header">
        <div className="panel-title">
          <AlertTriangle size={20} color="var(--danger)" />
          Live Alerts
        </div>
        <div
          className="status-badge"
          style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--danger)', borderColor: 'rgba(239,68,68,0.2)' }}
        >
          {alerts.length} Triggered
        </div>
      </div>
      <div className="alerts-list">
        {alerts.length === 0 ? (
          <div className="empty-state-inline">
            <ShieldCheck size={32} color="var(--text-muted)" />
            <p>No alerts triggered</p>
          </div>
        ) : (
          alerts.map((alert) => (
            <div key={alert.id} className={`alert-item alert-${alert.type}`}>
              <div className="alert-content">
                <div className="alert-title">{alert.title}</div>
                <div className="alert-time">{alert.cam} • {alert.time}</div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
