import { useState } from 'react';
import { Camera, Plus, Trash2, Wifi, X } from 'lucide-react';
import { useApi, apiPost, apiDelete } from '../hooks/useApi';
import StatusBadge from '../components/StatusBadge';
import EmptyState from '../components/EmptyState';
import type { Camera as CameraType } from '../types';

const sourceTypeLabels: Record<string, string> = {
  webcam: 'Webcam',
  rtsp: 'RTSP Stream',
  ip: 'IP Camera',
  file: 'Video File',
};

export default function CamerasPage() {
  const { data: cameras, loading, error, refetch } = useApi<CameraType[]>('/cameras');
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ name: '', source_url: '', source_type: 'webcam' });
  const [formError, setFormError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!formData.name.trim()) { setFormError('Name is required'); return; }
    try {
      await apiPost('/cameras', formData);
      setFormData({ name: '', source_url: '', source_type: 'webcam' });
      setShowForm(false);
      setFormError(null);
      refetch();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to create camera');
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete camera "${name}"?`)) return;
    try {
      await apiDelete(`/cameras/${id}`);
      refetch();
    } catch { /* ignore */ }
  };

  if (loading) return <div className="page-loading">Loading cameras…</div>;
  if (error) return <div className="page-error">Error: {error} <button className="btn btn-outline btn-sm" onClick={refetch}>Retry</button></div>;

  return (
    <div className="page-container animate-slide-in">
      {/* Header */}
      <div className="page-header">
        <div>
          <h2>Connected Cameras</h2>
          <p className="page-subtitle">{cameras?.length ?? 0} cameras configured</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? <><X size={18} /> Cancel</> : <><Plus size={18} /> Add Camera</>}
        </button>
      </div>

      {/* Add Camera Form */}
      {showForm && (
        <div className="glass-panel form-card">
          <h3 style={{ marginBottom: 16 }}>New Camera</h3>
          <div className="form-grid">
            <div className="form-group">
              <label>Camera Name</label>
              <input
                type="text"
                placeholder="e.g. Lobby Entrance"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>Source URL</label>
              <input
                type="text"
                placeholder="e.g. rtsp://192.168.1.100:554/stream"
                value={formData.source_url}
                onChange={(e) => setFormData({ ...formData, source_url: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>Source Type</label>
              <select
                value={formData.source_type}
                onChange={(e) => setFormData({ ...formData, source_type: e.target.value })}
              >
                <option value="webcam">Webcam</option>
                <option value="rtsp">RTSP Stream</option>
                <option value="ip">IP Camera</option>
                <option value="file">Video File</option>
              </select>
            </div>
          </div>
          {formError && <p className="form-error">{formError}</p>}
          <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={handleCreate}>
            <Plus size={16} /> Add Camera
          </button>
        </div>
      )}

      {/* Camera Grid */}
      {!cameras || cameras.length === 0 ? (
        <EmptyState
          icon={Camera}
          title="No Cameras Configured"
          description="Add your first camera to start real-time detection."
          action={{ label: 'Add Camera', onClick: () => setShowForm(true) }}
        />
      ) : (
        <div className="camera-grid">
          {cameras.map((cam) => (
            <div key={cam.id} className="glass-card camera-card">
              <div className="camera-preview">
                {cam.source_type === 'webcam' ? (
                  <Wifi size={32} color="var(--accent-primary)" />
                ) : (
                  <Camera size={32} color="var(--text-muted)" />
                )}
              </div>
              <div className="camera-info">
                <div className="camera-name">{cam.name}</div>
                <div className="camera-meta">
                  <span className="source-type-badge">{sourceTypeLabels[cam.source_type] ?? cam.source_type}</span>
                  <StatusBadge status={cam.is_active ? 'online' : 'offline'} />
                </div>
                <div className="camera-url" title={cam.source_url}>
                  {cam.source_url.length > 35 ? cam.source_url.slice(0, 35) + '…' : cam.source_url}
                </div>
              </div>
              <button
                className="btn-icon btn-icon-danger"
                onClick={() => handleDelete(cam.id, cam.name)}
                title="Delete camera"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
