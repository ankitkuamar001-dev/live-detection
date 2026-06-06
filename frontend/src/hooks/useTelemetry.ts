import { useEffect, useRef, useState, useCallback } from 'react';
import { WS_URL } from '../config';
import type { TelemetryStats, Alert, EmotionDataPoint } from '../types';

type ConnectionState = 'connecting' | 'connected' | 'disconnected';

interface TelemetryReturn {
  emotions: EmotionDataPoint[];
  alerts: Alert[];
  stats: TelemetryStats;
  connectionState: ConnectionState;
}

const DEFAULT_STATS: TelemetryStats = {
  total_detections: 0,
  total_people: 0,
  mask_compliance_pct: 0,
  emotions: {},
};

export function useTelemetry(): TelemetryReturn {
  const [emotions, setEmotions] = useState<EmotionDataPoint[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [stats, setStats] = useState<TelemetryStats>(DEFAULT_STATS);
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');

  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout>>(undefined);
  const reconnectDelay = useRef(1000);
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;

    setConnectionState('connecting');

    const socket = new WebSocket(`${WS_URL}/telemetry`);
    ws.current = socket;

    socket.onopen = () => {
      if (!mountedRef.current) return;
      setConnectionState('connected');
      reconnectDelay.current = 1000; // reset backoff
    };

    socket.onmessage = (event) => {
      if (!mountedRef.current) return;
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'init') {
          setEmotions(data.emotions ?? []);
          setAlerts(data.alerts ?? []);
        } else if (data.type === 'stats') {
          setStats(data.stats ?? DEFAULT_STATS);
          if (data.emotions) setEmotions(data.emotions);
        } else if (data.type === 'alert') {
          setAlerts((prev) => [data.alert, ...prev].slice(0, 50));
        }
      } catch {
        // ignore parse errors
      }
    };

    socket.onclose = () => {
      if (!mountedRef.current) return;
      setConnectionState('disconnected');
      // Exponential backoff reconnect
      reconnectTimeout.current = setTimeout(() => {
        reconnectDelay.current = Math.min(reconnectDelay.current * 2, 8000);
        connect();
      }, reconnectDelay.current);
    };

    socket.onerror = () => {
      socket.close();
    };
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      clearTimeout(reconnectTimeout.current);
      ws.current?.close();
    };
  }, [connect]);

  return { emotions, alerts, stats, connectionState };
}
