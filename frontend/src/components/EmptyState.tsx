import type { ElementType } from 'react';

interface EmptyStateProps {
  icon: ElementType;
  title: string;
  description: string;
  action?: { label: string; onClick: () => void };
}

export default function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <Icon size={56} color="var(--text-muted)" style={{ opacity: 0.6, marginBottom: 16 }} />
      <h3>{title}</h3>
      <p style={{ color: 'var(--text-muted)', marginTop: 8, maxWidth: 400, textAlign: 'center', lineHeight: 1.6 }}>
        {description}
      </p>
      {action && (
        <button className="btn btn-primary" style={{ marginTop: 20 }} onClick={action.onClick}>
          {action.label}
        </button>
      )}
    </div>
  );
}
