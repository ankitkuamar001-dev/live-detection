import VideoFeed from '../components/VideoFeed';
import StatsPanel from '../components/StatsPanel';
import EmotionChart from '../components/EmotionChart';
import AlertList from '../components/AlertList';
import type { TelemetryStats, Alert, EmotionDataPoint } from '../types';

interface DashboardPageProps {
  stats: TelemetryStats;
  alerts: Alert[];
  emotions: EmotionDataPoint[];
}

export default function DashboardPage({ stats, alerts, emotions }: DashboardPageProps) {
  return (
    <div className="dashboard">
      <div className="main-feed">
        <VideoFeed />
        <StatsPanel stats={stats} />
      </div>
      <div className="side-panel">
        <AlertList alerts={alerts} />
        <EmotionChart emotions={emotions} />
      </div>
    </div>
  );
}
