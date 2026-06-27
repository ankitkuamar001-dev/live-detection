import { useState } from 'react';
import { useTelemetry } from './hooks/useTelemetry';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import DashboardPage from './pages/DashboardPage';
import CamerasPage from './pages/CamerasPage';
import RecordingsPage from './pages/RecordingsPage';
import AnalyticsPage from './pages/AnalyticsPage';
import AlertRulesPage from './pages/AlertRulesPage';
import SettingsPage from './pages/SettingsPage';
import type { TabId } from './types';

const TAB_TITLES: Record<TabId, string> = {
  dashboard: 'Overview',
  cameras: 'Cameras Management',
  recordings: 'Recordings & History',
  analytics: 'Historical Analytics',
  alerts: 'Alert Rules Configuration',
  settings: 'System Settings',
};

function App() {
  const [activeTab, setActiveTab] = useState<TabId>('dashboard');
  const { emotions, alerts, stats, connectionState } = useTelemetry();

  return (
    <div className="app-container">
      <Sidebar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        alertCount={alerts.length}
      />

      <main className="main-content">
        <Header
          title={TAB_TITLES[activeTab]}
          connectionState={connectionState}
        />

        {activeTab === 'dashboard' && (
          <DashboardPage stats={stats} alerts={alerts} emotions={emotions} />
        )}
        {activeTab === 'cameras' && <CamerasPage />}
        {activeTab === 'recordings' && <RecordingsPage />}
        {activeTab === 'analytics' && <AnalyticsPage />}
        {activeTab === 'alerts' && <AlertRulesPage />}
        {activeTab === 'settings' && <SettingsPage />}
      </main>
    </div>
  );
}

export default App;
