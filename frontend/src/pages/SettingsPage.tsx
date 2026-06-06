import { useState } from 'react';
import { Cpu, HardDrive, Zap, Save, Monitor, RefreshCw } from 'lucide-react';
import { useApi, apiPut } from '../hooks/useApi';
import StatusBadge from '../components/StatusBadge';
import type { SystemInfo, ModelInfo, RuntimeSettings } from '../types';

export default function SettingsPage() {
  const { data: sysInfo, loading: sysLoading, refetch: refetchSys } = useApi<SystemInfo>('/system/info');
  const { data: models, loading: modelsLoading, refetch: refetchModels } = useApi<ModelInfo[]>('/system/models');
  const { data: settings, loading: settingsLoading, refetch: refetchSettings } = useApi<RuntimeSettings>('/settings');

  const [editConf, setEditConf] = useState<number | null>(null);
  const [editFps, setEditFps] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  const handleSave = async () => {
    setSaving(true);
    setSaveMsg(null);
    try {
      const body: Record<string, number> = {};
      if (editConf !== null) body.confidence_threshold = editConf;
      if (editFps !== null) body.target_fps = editFps;
      await apiPut('/settings', body);
      setSaveMsg('Settings saved!');
      refetchSettings();
      setTimeout(() => setSaveMsg(null), 3000);
    } catch {
      setSaveMsg('Failed to save settings.');
    } finally {
      setSaving(false);
    }
  };

  const isLoading = sysLoading || modelsLoading || settingsLoading;
  if (isLoading) return <div className="page-loading">Loading system info…</div>;

  const confValue = editConf ?? settings?.confidence_threshold ?? 0.5;
  const fpsValue = editFps ?? settings?.target_fps ?? 15;

  return (
    <div className="page-container animate-slide-in">
      <div className="page-header">
        <div>
          <h2>System Settings</h2>
          <p className="page-subtitle">Monitor hardware and configure runtime parameters</p>
        </div>
        <button className="btn btn-outline" onClick={() => { refetchSys(); refetchModels(); refetchSettings(); }}>
          <RefreshCw size={16} /> Refresh
        </button>
      </div>

      <div className="settings-grid">
        {/* System Information */}
        <div className="glass-panel settings-card">
          <h3 className="settings-card-title"><Monitor size={18} /> System Information</h3>
          <div className="info-rows">
            <div className="info-row">
              <span className="info-label">Platform</span>
              <span className="info-value">{sysInfo?.platform ?? '—'}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Python</span>
              <span className="info-value">{sysInfo?.python_version ?? '—'}</span>
            </div>
            <div className="info-row">
              <span className="info-label">CPU Cores</span>
              <span className="info-value"><Cpu size={14} /> {sysInfo?.cpu_count ?? '—'}</span>
            </div>
            <div className="info-row">
              <span className="info-label">RAM</span>
              <span className="info-value">{sysInfo?.total_ram_gb ?? 0} GB</span>
            </div>
            <div className="info-row">
              <span className="info-label">Disk Usage</span>
              <div style={{ flex: 1 }}>
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${sysInfo?.disk_usage_percent ?? 0}%` }} />
                </div>
                <span className="info-value" style={{ fontSize: '0.75rem' }}>
                  {sysInfo?.disk_used_gb ?? 0} / {sysInfo?.disk_total_gb ?? 0} GB ({sysInfo?.disk_usage_percent ?? 0}%)
                </span>
              </div>
            </div>
            <div className="info-row">
              <span className="info-label">GPU</span>
              <span className="info-value">
                {sysInfo?.gpu_available ? (
                  <><Zap size={14} color="var(--success)" /> {sysInfo.gpu_name}</>
                ) : (
                  <span style={{ color: 'var(--text-muted)' }}>Not available (CPU mode)</span>
                )}
              </span>
            </div>
          </div>
        </div>

        {/* Loaded Models */}
        <div className="glass-panel settings-card">
          <h3 className="settings-card-title"><HardDrive size={18} /> Loaded Models</h3>
          <div className="models-list">
            {models?.map((model, i) => (
              <div key={i} className="model-item">
                <div>
                  <div className="model-name">{model.name}</div>
                  <div className="model-type">{model.type} • {model.device}</div>
                </div>
                <StatusBadge status={model.status as 'loaded' | 'error' | 'not_found'} />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Runtime Configuration */}
      <div className="glass-panel settings-card" style={{ marginTop: 24 }}>
        <h3 className="settings-card-title"><Zap size={18} /> Runtime Configuration</h3>
        <div className="form-grid" style={{ marginTop: 16 }}>
          <div className="form-group">
            <label>Model</label>
            <input type="text" value={settings?.model_name ?? 'yolo11n.pt'} disabled className="input-disabled" />
          </div>
          <div className="form-group">
            <label>Device</label>
            <input type="text" value={settings?.device ?? 'cpu'} disabled className="input-disabled" />
          </div>
          <div className="form-group">
            <label>Confidence Threshold: {confValue.toFixed(2)}</label>
            <input
              type="range"
              min={0.1}
              max={1.0}
              step={0.05}
              value={confValue}
              onChange={(e) => setEditConf(parseFloat(e.target.value))}
              className="range-input"
            />
          </div>
          <div className="form-group">
            <label>Target FPS</label>
            <input
              type="number"
              min={1}
              max={120}
              value={fpsValue}
              onChange={(e) => setEditFps(parseInt(e.target.value) || 15)}
            />
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 20 }}>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            <Save size={16} /> {saving ? 'Saving…' : 'Save Changes'}
          </button>
          {saveMsg && <span style={{ color: saveMsg.includes('Failed') ? 'var(--danger)' : 'var(--success)', fontSize: '0.875rem' }}>{saveMsg}</span>}
        </div>
      </div>
    </div>
  );
}
