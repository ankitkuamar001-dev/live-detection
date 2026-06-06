import { useState } from 'react';
import { AlertTriangle, Plus, Trash2, X, Clock, Zap, ShieldCheck } from 'lucide-react';
import { useApi, apiPost, apiPut, apiDelete } from '../hooks/useApi';
import EmptyState from '../components/EmptyState';
import type { AlertRule, Alert } from '../types';

const eventTypeLabels: Record<string, { label: string; color: string }> = {
  no_mask:            { label: 'No Mask', color: 'var(--danger)' },
  crowd:              { label: 'Crowd', color: 'var(--warning)' },
  intrusion:          { label: 'Intrusion', color: 'var(--danger)' },
  aggressive_emotion: { label: 'Aggressive Emotion', color: '#8b5cf6' },
  custom:             { label: 'Custom', color: 'var(--accent-primary)' },
};

export default function AlertRulesPage() {
  const { data: rules, loading, error, refetch } = useApi<AlertRule[]>('/alerts/rules');
  const { data: history } = useApi<Alert[]>('/alerts/history');
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    name: '', event_type: 'no_mask', cooldown_seconds: 60, channels: ['log'], is_active: true,
  });
  const [formError, setFormError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!formData.name.trim()) { setFormError('Rule name is required'); return; }
    try {
      await apiPost('/alerts/rules', { ...formData, conditions: {} });
      setFormData({ name: '', event_type: 'no_mask', cooldown_seconds: 60, channels: ['log'], is_active: true });
      setShowForm(false);
      setFormError(null);
      refetch();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to create rule');
    }
  };

  const handleToggle = async (rule: AlertRule) => {
    try {
      await apiPut(`/alerts/rules/${rule.id}`, { is_active: !rule.is_active });
      refetch();
    } catch { /* ignore */ }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete rule "${name}"?`)) return;
    try {
      await apiDelete(`/alerts/rules/${id}`);
      refetch();
    } catch { /* ignore */ }
  };

  const toggleChannel = (ch: string) => {
    setFormData((prev) => ({
      ...prev,
      channels: prev.channels.includes(ch)
        ? prev.channels.filter((c) => c !== ch)
        : [...prev.channels, ch],
    }));
  };

  if (loading) return <div className="page-loading">Loading alert rules…</div>;
  if (error) return <div className="page-error">Error: {error} <button className="btn btn-outline btn-sm" onClick={refetch}>Retry</button></div>;

  return (
    <div className="page-container animate-slide-in">
      {/* Header */}
      <div className="page-header">
        <div>
          <h2>Alert Rules</h2>
          <p className="page-subtitle">{rules?.length ?? 0} rules configured</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? <><X size={18} /> Cancel</> : <><Plus size={18} /> Create Rule</>}
        </button>
      </div>

      {/* Create Form */}
      {showForm && (
        <div className="glass-panel form-card">
          <h3 style={{ marginBottom: 16 }}>New Alert Rule</h3>
          <div className="form-grid">
            <div className="form-group">
              <label>Rule Name</label>
              <input
                type="text"
                placeholder="e.g. Entrance No-Mask Alert"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>Event Type</label>
              <select
                value={formData.event_type}
                onChange={(e) => setFormData({ ...formData, event_type: e.target.value })}
              >
                <option value="no_mask">No Mask Detected</option>
                <option value="crowd">Crowd Detection</option>
                <option value="intrusion">Zone Intrusion</option>
                <option value="aggressive_emotion">Aggressive Emotion</option>
              </select>
            </div>
            <div className="form-group">
              <label>Cooldown (seconds)</label>
              <input
                type="number"
                min={0}
                max={3600}
                value={formData.cooldown_seconds}
                onChange={(e) => setFormData({ ...formData, cooldown_seconds: parseInt(e.target.value) || 0 })}
              />
            </div>
          </div>
          <div className="form-group" style={{ marginTop: 12 }}>
            <label>Channels</label>
            <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
              {['log', 'email', 'telegram'].map((ch) => (
                <label key={ch} className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={formData.channels.includes(ch)}
                    onChange={() => toggleChannel(ch)}
                  />
                  {ch.charAt(0).toUpperCase() + ch.slice(1)}
                </label>
              ))}
            </div>
          </div>
          {formError && <p className="form-error">{formError}</p>}
          <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={handleCreate}>
            <Plus size={16} /> Create Rule
          </button>
        </div>
      )}

      {/* Rules List */}
      {!rules || rules.length === 0 ? (
        <EmptyState
          icon={ShieldCheck}
          title="No Alert Rules"
          description="Create alert rules to get notified about mask violations, crowd events, and more."
          action={{ label: 'Create Rule', onClick: () => setShowForm(true) }}
        />
      ) : (
        <div className="rules-grid">
          {rules.map((rule) => {
            const et = eventTypeLabels[rule.event_type] ?? eventTypeLabels.custom;
            return (
              <div key={rule.id} className={`glass-card rule-card${!rule.is_active ? ' rule-disabled' : ''}`}>
                <div className="rule-header">
                  <div>
                    <div className="rule-name">{rule.name}</div>
                    <span className="event-type-badge" style={{ color: et.color, borderColor: et.color }}>
                      <Zap size={12} /> {et.label}
                    </span>
                  </div>
                  <button
                    className={`toggle-btn ${rule.is_active ? 'toggle-on' : 'toggle-off'}`}
                    onClick={() => handleToggle(rule)}
                    title={rule.is_active ? 'Disable' : 'Enable'}
                  >
                    <div className="toggle-knob" />
                  </button>
                </div>
                <div className="rule-meta">
                  <span><Clock size={13} /> {rule.cooldown_seconds}s cooldown</span>
                  <span>Channels: {rule.channels.join(', ')}</span>
                </div>
                <button className="btn-icon btn-icon-danger rule-delete" onClick={() => handleDelete(rule.id, rule.name)}>
                  <Trash2 size={14} />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Alert History */}
      {history && history.length > 0 && (
        <div style={{ marginTop: 32 }}>
          <h3 style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <AlertTriangle size={20} color="var(--warning)" /> Alert History
          </h3>
          <div className="glass-panel" style={{ maxHeight: 300, overflowY: 'auto', padding: 0 }}>
            {history.map((alert) => (
              <div key={alert.id} className="history-item">
                <span className={`history-dot dot-${alert.type}`} />
                <span className="history-title">{alert.title}</span>
                <span className="history-time">{alert.cam} • {new Date(alert.time).toLocaleString()}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
