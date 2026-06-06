// ── Telemetry ──────────────────────────────────────────────────────────

export interface TelemetryStats {
  total_detections: number;
  total_people: number;
  mask_compliance_pct: number;
  emotions: Record<string, number>;
}

export interface Alert {
  id: string;
  type: 'warning' | 'danger' | 'info';
  title: string;
  cam: string;
  time: string;
  rule_name?: string;
}

export interface EmotionDataPoint {
  time: string;
  happy: number;
  sad: number;
  angry: number;
  fear: number;
  neutral: number;
  surprise: number;
}

// ── Cameras ────────────────────────────────────────────────────────────

export interface Camera {
  id: string;
  name: string;
  source_url: string;
  source_type: 'webcam' | 'rtsp' | 'ip' | 'file';
  is_active: boolean;
  status?: 'online' | 'offline' | 'error';
  fps?: number;
  created_at?: string;
}

// ── Recordings ─────────────────────────────────────────────────────────

export interface Recording {
  filename: string;
  size_bytes: number;
  size_display: string;
  created_at: string;
  duration?: string;
}

export interface RecordingStats {
  total_count: number;
  total_size_bytes: number;
  total_size_display: string;
}

// ── Alert Rules ────────────────────────────────────────────────────────

export interface AlertRule {
  id: string;
  name: string;
  event_type: string;
  conditions: Record<string, unknown>;
  channels: string[];
  cooldown_seconds: number;
  is_active: boolean;
  created_at?: string;
}

// ── System ─────────────────────────────────────────────────────────────

export interface SystemInfo {
  platform: string;
  python_version: string;
  cpu_count: number;
  total_ram_gb: number;
  disk_total_gb: number;
  disk_used_gb: number;
  disk_usage_percent: number;
  gpu_available: boolean;
  gpu_name?: string;
}

export interface ModelInfo {
  name: string;
  type: string;
  status: 'loaded' | 'error' | 'not_found';
  device: string;
  size?: string;
}

export interface RuntimeSettings {
  model_name: string;
  confidence_threshold: number;
  target_fps: number;
  device: string;
  debug: boolean;
}

// ── Navigation ─────────────────────────────────────────────────────────

export type TabId = 'dashboard' | 'cameras' | 'recordings' | 'alerts' | 'settings';
