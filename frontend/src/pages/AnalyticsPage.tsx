import { useState, useEffect, useCallback } from 'react';
import { API_BASE } from '../config';
import type { AnalyticsSummary, AnalyticsHourly, DetectionEvent } from '../types';

const EMOTION_COLORS: Record<string, string> = {
  happy: '#22c55e',
  sad: '#3b82f6',
  angry: '#ef4444',
  fear: '#f59e0b',
  neutral: '#94a3b8',
  surprise: '#a855f7',
  disgust: '#84cc16',
  contempt: '#6366f1',
};

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [hourly, setHourly] = useState<AnalyticsHourly[]>([]);
  const [events, setEvents] = useState<DetectionEvent[]>([]);
  const [hours, setHours] = useState(24);
  const [eventType, setEventType] = useState<string>('');
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [sumRes, hourRes, evRes] = await Promise.all([
        fetch(`${API_BASE}/analytics/summary?hours=${hours}`),
        fetch(`${API_BASE}/analytics/hourly?hours=${hours}`),
        fetch(`${API_BASE}/analytics/events?limit=50${eventType ? `&detection_type=${eventType}` : ''}`),
      ]);
      if (sumRes.ok) setSummary(await sumRes.json());
      if (hourRes.ok) setHourly(await hourRes.json());
      if (evRes.ok) setEvents(await evRes.json());
    } catch (err) {
      console.error('Failed to fetch analytics:', err);
    }
    setLoading(false);
  }, [hours, eventType]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Compute chart data from hourly
  const maxDetections = Math.max(1, ...hourly.map(h => h.total_detections));

  return (
    <div className="page-content">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 className="page-title">📊 Analytics</h1>
          <p className="page-subtitle">Historical detection data and trends</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <select
            value={hours}
            onChange={e => setHours(Number(e.target.value))}
            className="form-select"
            style={{ padding: '0.5rem 1rem', borderRadius: '8px', background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
          >
            <option value={6}>Last 6 hours</option>
            <option value={12}>Last 12 hours</option>
            <option value={24}>Last 24 hours</option>
            <option value={48}>Last 48 hours</option>
            <option value={168}>Last 7 days</option>
          </select>
          <button onClick={fetchData} className="btn-primary" style={{ padding: '0.5rem 1rem', borderRadius: '8px', background: 'var(--accent)', color: '#fff', border: 'none', cursor: 'pointer' }}>
            ↻ Refresh
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>Loading analytics...</div>
      ) : (
        <>
          {/* Summary Cards */}
          {summary && (
            <div className="stats-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
              <SummaryCard title="Total Events" value={summary.total_events.toLocaleString()} icon="📋" color="var(--accent)" />
              <SummaryCard title="Mask Compliance" value={`${summary.mask_compliance_pct}%`} icon="😷" color={summary.mask_compliance_pct >= 80 ? '#22c55e' : '#ef4444'} />
              <SummaryCard title="Active Cameras" value={String(summary.active_cameras)} icon="📹" color="#8b5cf6" />
              <SummaryCard
                title="Top Emotion"
                value={Object.entries(summary.emotion_breakdown || {}).sort((a, b) => b[1] - a[1])[0]?.[0] || 'N/A'}
                icon="🎭"
                color="#f59e0b"
              />
            </div>
          )}

          {/* Detection Type Breakdown */}
          {summary && Object.keys(summary.by_type || {}).length > 0 && (
            <div className="card" style={{ marginBottom: '1.5rem', padding: '1.25rem', borderRadius: '12px', background: 'var(--surface-2)', border: '1px solid var(--border)' }}>
              <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem', color: 'var(--text-primary)' }}>Detection Type Distribution</h3>
              <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
                {Object.entries(summary.by_type).map(([type, count]) => (
                  <div key={type} style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--accent)' }}>{count.toLocaleString()}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'capitalize' }}>{type}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Hourly Bar Chart */}
          {hourly.length > 0 && (
            <div className="card" style={{ marginBottom: '1.5rem', padding: '1.25rem', borderRadius: '12px', background: 'var(--surface-2)', border: '1px solid var(--border)' }}>
              <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem', color: 'var(--text-primary)' }}>Detections Over Time</h3>
              <div style={{ display: 'flex', gap: '2px', alignItems: 'flex-end', height: '160px', padding: '0.5rem 0' }}>
                {hourly.map((h, i) => {
                  const pct = (h.total_detections / maxDetections) * 100;
                  const hour = h.hour ? new Date(h.hour).getHours() : i;
                  return (
                    <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end', height: '100%' }} title={`${h.total_detections} detections at ${hour}:00`}>
                      <div style={{
                        width: '100%',
                        maxWidth: '20px',
                        minHeight: '2px',
                        height: `${Math.max(2, pct)}%`,
                        background: `linear-gradient(180deg, var(--accent), #3b82f6)`,
                        borderRadius: '3px 3px 0 0',
                        transition: 'height 0.3s ease',
                      }} />
                      {hourly.length <= 24 && (
                        <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)', marginTop: '4px' }}>{hour}h</span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Mask Breakdown + Emotion Breakdown */}
          {summary && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
              {/* Mask Pie */}
              <div className="card" style={{ padding: '1.25rem', borderRadius: '12px', background: 'var(--surface-2)', border: '1px solid var(--border)' }}>
                <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem', color: 'var(--text-primary)' }}>Mask Compliance</h3>
                {Object.keys(summary.mask_breakdown || {}).length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    {Object.entries(summary.mask_breakdown).map(([label, count]) => {
                      const total = Object.values(summary.mask_breakdown).reduce((a, b) => a + b, 0);
                      const pct = total > 0 ? (count / total * 100).toFixed(1) : '0';
                      return (
                        <div key={label}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', textTransform: 'capitalize' }}>{label.replace('_', ' ')}</span>
                            <span style={{ fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 600 }}>{count} ({pct}%)</span>
                          </div>
                          <div style={{ height: '6px', borderRadius: '3px', background: 'var(--border)', overflow: 'hidden' }}>
                            <div style={{ height: '100%', width: `${pct}%`, background: label === 'with_mask' ? '#22c55e' : '#ef4444', borderRadius: '3px', transition: 'width 0.5s ease' }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p style={{ color: 'var(--text-muted)', margin: 0 }}>No mask data yet</p>
                )}
              </div>

              {/* Emotion Distribution */}
              <div className="card" style={{ padding: '1.25rem', borderRadius: '12px', background: 'var(--surface-2)', border: '1px solid var(--border)' }}>
                <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem', color: 'var(--text-primary)' }}>Emotion Distribution</h3>
                {Object.keys(summary.emotion_breakdown || {}).length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    {Object.entries(summary.emotion_breakdown).sort((a, b) => b[1] - a[1]).map(([emotion, count]) => {
                      const total = Object.values(summary.emotion_breakdown).reduce((a, b) => a + b, 0);
                      const pct = total > 0 ? (count / total * 100).toFixed(1) : '0';
                      return (
                        <div key={emotion}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', textTransform: 'capitalize' }}>{emotion}</span>
                            <span style={{ fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 600 }}>{count} ({pct}%)</span>
                          </div>
                          <div style={{ height: '6px', borderRadius: '3px', background: 'var(--border)', overflow: 'hidden' }}>
                            <div style={{ height: '100%', width: `${pct}%`, background: EMOTION_COLORS[emotion] || '#64748b', borderRadius: '3px', transition: 'width 0.5s ease' }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p style={{ color: 'var(--text-muted)', margin: 0 }}>No emotion data yet</p>
                )}
              </div>
            </div>
          )}

          {/* Recent Events Table */}
          <div className="card" style={{ padding: '1.25rem', borderRadius: '12px', background: 'var(--surface-2)', border: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ margin: 0, fontSize: '1rem', color: 'var(--text-primary)' }}>Recent Events</h3>
              <select
                value={eventType}
                onChange={e => setEventType(e.target.value)}
                style={{ padding: '0.4rem 0.75rem', borderRadius: '6px', background: 'var(--surface-1)', border: '1px solid var(--border)', color: 'var(--text-primary)', fontSize: '0.8rem' }}
              >
                <option value="">All Types</option>
                <option value="mask">Mask</option>
                <option value="emotion">Emotion</option>
                <option value="object">Object</option>
              </select>
            </div>

            {events.length > 0 ? (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border)' }}>
                      <th style={{ padding: '0.5rem', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 500 }}>Time</th>
                      <th style={{ padding: '0.5rem', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 500 }}>Camera</th>
                      <th style={{ padding: '0.5rem', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 500 }}>Type</th>
                      <th style={{ padding: '0.5rem', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 500 }}>Label</th>
                      <th style={{ padding: '0.5rem', textAlign: 'right', color: 'var(--text-muted)', fontWeight: 500 }}>Confidence</th>
                      <th style={{ padding: '0.5rem', textAlign: 'right', color: 'var(--text-muted)', fontWeight: 500 }}>Track</th>
                    </tr>
                  </thead>
                  <tbody>
                    {events.map(ev => (
                      <tr key={ev.id} style={{ borderBottom: '1px solid var(--border)', transition: 'background 0.15s' }}>
                        <td style={{ padding: '0.5rem', color: 'var(--text-secondary)' }}>{ev.detected_at ? new Date(ev.detected_at).toLocaleTimeString() : '-'}</td>
                        <td style={{ padding: '0.5rem', color: 'var(--text-secondary)' }}>{ev.camera_id}</td>
                        <td style={{ padding: '0.5rem' }}>
                          <span style={{
                            padding: '2px 8px',
                            borderRadius: '4px',
                            fontSize: '0.7rem',
                            fontWeight: 600,
                            background: ev.detection_type === 'mask' ? '#22c55e22' : ev.detection_type === 'emotion' ? '#f59e0b22' : '#3b82f622',
                            color: ev.detection_type === 'mask' ? '#22c55e' : ev.detection_type === 'emotion' ? '#f59e0b' : '#3b82f6',
                          }}>{ev.detection_type}</span>
                        </td>
                        <td style={{ padding: '0.5rem', color: 'var(--text-primary)', fontWeight: 500, textTransform: 'capitalize' }}>{ev.label?.replace('_', ' ')}</td>
                        <td style={{ padding: '0.5rem', textAlign: 'right', color: 'var(--text-secondary)', fontFamily: 'monospace' }}>{(ev.confidence * 100).toFixed(1)}%</td>
                        <td style={{ padding: '0.5rem', textAlign: 'right', color: 'var(--text-muted)' }}>{ev.track_id ?? '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p style={{ color: 'var(--text-muted)', textAlign: 'center', margin: '2rem 0' }}>No events recorded yet. Start a camera to begin collecting data.</p>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function SummaryCard({ title, value, icon, color }: { title: string; value: string; icon: string; color: string }) {
  return (
    <div style={{
      padding: '1.25rem',
      borderRadius: '12px',
      background: 'var(--surface-2)',
      border: '1px solid var(--border)',
      display: 'flex',
      alignItems: 'center',
      gap: '1rem',
    }}>
      <div style={{ fontSize: '2rem', lineHeight: 1 }}>{icon}</div>
      <div>
        <div style={{ fontSize: '1.5rem', fontWeight: 700, color, lineHeight: 1.2 }}>{value}</div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>{title}</div>
      </div>
    </div>
  );
}
