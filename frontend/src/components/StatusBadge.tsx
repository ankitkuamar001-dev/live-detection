interface StatusBadgeProps {
  status: 'online' | 'offline' | 'error' | 'loaded' | 'not_found';
  label?: string;
}

const statusStyles: Record<string, { color: string; bg: string }> = {
  online:    { color: 'var(--success)', bg: 'rgba(16,185,129,0.15)' },
  loaded:    { color: 'var(--success)', bg: 'rgba(16,185,129,0.15)' },
  offline:   { color: 'var(--text-muted)', bg: 'rgba(100,116,139,0.15)' },
  error:     { color: 'var(--danger)', bg: 'rgba(239,68,68,0.15)' },
  not_found: { color: 'var(--warning)', bg: 'rgba(245,158,11,0.15)' },
};

export default function StatusBadge({ status, label }: StatusBadgeProps) {
  const s = statusStyles[status] ?? statusStyles.offline;
  return (
    <span
      className="status-badge-sm"
      style={{ color: s.color, background: s.bg }}
    >
      <span
        className={status === 'online' || status === 'loaded' ? 'dot-pulse' : 'dot-static'}
        style={{ background: s.color }}
      />
      {label ?? status}
    </span>
  );
}
