import { useState } from 'react';
import { Video, Play, Trash2, Database, FileVideo, X } from 'lucide-react';
import { useApi, apiDelete } from '../hooks/useApi';
import { API_URL } from '../config';
import EmptyState from '../components/EmptyState';
import type { Recording, RecordingStats } from '../types';

export default function RecordingsPage() {
  const { data: recordings, loading, error, refetch } = useApi<Recording[]>('/recordings');
  const { data: stats } = useApi<RecordingStats>('/recordings/stats');
  const [playingFile, setPlayingFile] = useState<string | null>(null);

  const handleDelete = async (filename: string) => {
    if (!confirm(`Delete recording "${filename}"?`)) return;
    try {
      await apiDelete(`/recordings/${filename}`);
      if (playingFile === filename) setPlayingFile(null);
      refetch();
    } catch { /* ignore */ }
  };

  if (loading) return <div className="page-loading">Loading recordings…</div>;
  if (error) return <div className="page-error">Error: {error} <button className="btn btn-outline btn-sm" onClick={refetch}>Retry</button></div>;

  return (
    <div className="page-container animate-slide-in">
      {/* Header with storage stats */}
      <div className="page-header">
        <div>
          <h2>Recordings & History</h2>
          <p className="page-subtitle">Browse and manage recorded video clips</p>
        </div>
        {stats && (
          <div className="stats-inline">
            <div className="stat-chip">
              <FileVideo size={14} /> {stats.total_count} files
            </div>
            <div className="stat-chip">
              <Database size={14} /> {stats.total_size_display}
            </div>
          </div>
        )}
      </div>

      {/* Video Player */}
      {playingFile && (
        <div className="glass-panel" style={{ padding: 16, marginBottom: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 style={{ fontSize: '1rem' }}>▶ {playingFile}</h3>
            <button className="btn-icon" onClick={() => setPlayingFile(null)}><X size={18} /></button>
          </div>
          <video
            src={`${API_URL}/recordings/${playingFile}`}
            controls
            autoPlay
            style={{ width: '100%', maxHeight: 400, borderRadius: 'var(--radius-sm)', background: '#000' }}
          />
        </div>
      )}

      {/* Recordings List */}
      {!recordings || recordings.length === 0 ? (
        <EmptyState
          icon={Video}
          title="No Recordings Found"
          description="Recorded clips from detection events will appear here."
        />
      ) : (
        <div className="glass-panel" style={{ overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Filename</th>
                <th>Size</th>
                <th>Date</th>
                <th style={{ width: 120 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {recordings.map((rec) => (
                <tr key={rec.filename} className={playingFile === rec.filename ? 'row-active' : ''}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <FileVideo size={16} color="var(--accent-primary)" />
                      <span className="filename">{rec.filename}</span>
                    </div>
                  </td>
                  <td className="text-muted">{rec.size_display}</td>
                  <td className="text-muted">{new Date(rec.created_at).toLocaleDateString()}</td>
                  <td>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button
                        className="btn-icon"
                        onClick={() => setPlayingFile(rec.filename)}
                        title="Play"
                      >
                        <Play size={16} />
                      </button>
                      <button
                        className="btn-icon btn-icon-danger"
                        onClick={() => handleDelete(rec.filename)}
                        title="Delete"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
