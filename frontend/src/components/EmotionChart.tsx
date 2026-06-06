import { Activity } from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import type { EmotionDataPoint } from '../types';

interface EmotionChartProps {
  emotions: EmotionDataPoint[];
}

export default function EmotionChart({ emotions }: EmotionChartProps) {
  return (
    <div className="glass-panel chart-panel animate-slide-in" style={{ animationDelay: '0.2s' }}>
      <div className="panel-header">
        <div className="panel-title">
          <Activity size={20} color="var(--accent-primary)" />
          Live Emotion Trends
        </div>
      </div>
      <div style={{ width: '100%', height: 'calc(100% - 50px)' }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={emotions}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="time" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
            <YAxis stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1a1d24', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
              itemStyle={{ color: '#fff' }}
            />
            <Legend
              wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }}
              iconType="line"
            />
            <Line type="monotone" dataKey="happy" name="Happy" stroke="#10b981" strokeWidth={3} dot={false} activeDot={{ r: 6 }} isAnimationActive={false} />
            <Line type="monotone" dataKey="sad" name="Sad" stroke="#3b82f6" strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="angry" name="Angry" stroke="#ef4444" strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="fear" name="Fear" stroke="#8b5cf6" strokeWidth={2} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
