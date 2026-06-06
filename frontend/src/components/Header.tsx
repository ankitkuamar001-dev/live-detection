interface HeaderProps {
  title: string;
  connectionState: string;
}

export default function Header({ title, connectionState }: HeaderProps) {
  const stateMap: Record<string, { color: string; bg: string; border: string; label: string }> = {
    connected:    { color: 'var(--success)', bg: 'rgba(16,185,129,0.1)', border: 'rgba(16,185,129,0.2)', label: 'System Active' },
    connecting:   { color: 'var(--warning)', bg: 'rgba(245,158,11,0.1)', border: 'rgba(245,158,11,0.2)', label: 'Connecting…' },
    disconnected: { color: 'var(--danger)',  bg: 'rgba(239,68,68,0.1)',  border: 'rgba(239,68,68,0.2)',  label: 'Disconnected' },
  };
  const s = stateMap[connectionState] ?? stateMap.disconnected;

  return (
    <header className="top-header">
      <div className="header-title">{title}</div>
      <div className="header-actions">
        <div
          className="status-badge"
          style={{ background: s.bg, color: s.color, borderColor: s.border }}
        >
          <div className="status-dot" style={{ background: s.color, boxShadow: `0 0 10px ${s.color}` }} />
          {s.label}
        </div>
      </div>
    </header>
  );
}
