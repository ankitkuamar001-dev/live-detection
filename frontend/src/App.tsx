import React, { useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Camera,
  LayoutDashboard,
  Settings,
  Shield,
  Video,
  Users,
  Smile
} from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

import { useEffect, useRef } from 'react';

// --- WEBSOCKET HOOK ---
function useTelemetry() {
  const [emotions, setEmotions] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [stats, setStats] = useState({ total_detections: 0, mask_compliance_pct: 0 });
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    ws.current = new WebSocket('ws://localhost:8000/api/v1/ws/telemetry');
    
    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'init') {
          setEmotions(data.emotions);
          setAlerts(data.alerts);
        } else if (data.type === 'stats') {
          setStats(data.stats);
          setEmotions(data.emotions);
        } else if (data.type === 'alert') {
          setAlerts((prev) => [data.alert, ...prev].slice(0, 20));
        }
      } catch (e) {
        console.error("WebSocket parsing error", e);
      }
    };

    return () => {
      ws.current?.close();
    };
  }, []);

  return { emotions, alerts, stats };
}

// --- COMPONENTS ---

const VideoFeed = () => {
  const [isLive, setIsLive] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [useDeepEnhance, setUseDeepEnhance] = useState(false);
  const [processedVideoUrl, setProcessedVideoUrl] = useState<string | null>(null);

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setProcessedVideoUrl(null);
    setIsLive(false);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`http://localhost:8000/api/v1/video/upload?deep_enhance=${useDeepEnhance}`, {
        method: "POST",
        body: formData,
      });

      if (response.ok) {
        // Create an object URL from the returned blob (the processed video)
        const blob = await response.blob();
        setProcessedVideoUrl(URL.createObjectURL(blob));
      } else {
        alert("Failed to process video");
      }
    } catch (error) {
      console.error(error);
      alert("Error uploading video");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="glass-panel video-container animate-slide-in" style={{ display: 'flex', flexDirection: 'column' }}>
      
      {/* Video Content Area */}
      <div style={{ flex: 1, position: 'relative', background: '#000', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {isLive ? (
          <img 
            src="http://localhost:8000/api/v1/ws/video/live" 
            alt="Live Stream" 
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
            onError={() => { setIsLive(false); alert("Failed to connect to camera"); }}
          />
        ) : processedVideoUrl ? (
          <video 
            src={processedVideoUrl} 
            controls 
            autoPlay 
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          />
        ) : (
          <div className="video-placeholder" style={{ position: 'relative' }}>
            {isUploading ? (
              <>
                <Activity className="spinner" size={48} />
                <h3>Processing Video...</h3>
                <p style={{ color: 'var(--text-muted)', marginTop: '8px' }}>
                  {useDeepEnhance ? "Applying Real-ESRGAN Super-Resolution (This may take a long time)" : "Running YOLO11 Inference"}
                </p>
              </>
            ) : (
              <>
                <Camera size={48} color="var(--text-muted)" style={{ marginBottom: 16 }} />
                <h3>Camera Offline</h3>
                <p style={{ color: 'var(--text-muted)', marginTop: '8px' }}>Select an option below to start detection</p>
              </>
            )}
          </div>
        )}

        {/* Overlay info */}
        {(isLive || processedVideoUrl) && (
          <div className="video-overlay" style={{ position: 'absolute', top: 16, left: 16, right: 16 }}>
            <div className="cam-label">
              <span>●</span> {isLive ? "CAM 01 - Live Detection (OpenCV Enhancements)" : "Uploaded Video Processing"}
            </div>
          </div>
        )}
      </div>

      {/* Controls Area */}
      <div style={{ padding: '16px', borderTop: '1px solid var(--border-color)', display: 'flex', gap: '12px', background: 'rgba(0,0,0,0.2)', alignItems: 'center' }}>
        <button 
          onClick={() => { setIsLive(!isLive); setProcessedVideoUrl(null); }}
          style={{
            padding: '10px 20px',
            background: isLive ? 'rgba(239, 68, 68, 0.2)' : 'var(--accent-primary)',
            color: isLive ? 'var(--danger)' : '#fff',
            border: isLive ? '1px solid var(--danger)' : 'none',
            borderRadius: 'var(--radius-sm)',
            cursor: 'pointer',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <Video size={18} /> {isLive ? "Stop Camera" : "Start Live Camera"}
        </button>

        <label style={{
            padding: '10px 20px',
            background: 'rgba(255,255,255,0.05)',
            border: '1px solid var(--border-color)',
            color: '#fff',
            borderRadius: 'var(--radius-sm)',
            cursor: 'pointer',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
        }}>
          <Camera size={18} /> Upload Video
          <input type="file" accept="video/*" style={{ display: 'none' }} onChange={handleUpload} disabled={isUploading} />
        </label>
        
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <label style={{ color: 'var(--text-muted)', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
            <input 
              type="checkbox" 
              checked={useDeepEnhance} 
              onChange={(e) => setUseDeepEnhance(e.target.checked)}
              disabled={isUploading || isLive}
            />
            Use Real-ESRGAN (Deep AI Enhance)
          </label>
        </div>
      </div>
    </div>
  );
};

const StatsPanel = ({ stats }) => (
  <div className="stats-grid animate-slide-in" style={{ animationDelay: '0.1s' }}>
    <div className="glass-card stat-card">
      <div className="stat-header">
        <Users size={16} color="var(--accent-primary)" />
        Total Live Detections
      </div>
      <div className="stat-value">{stats.total_detections}</div>
      <div className="stat-trend trend-up">Current Frame</div>
    </div>
    
    <div className="glass-card stat-card">
      <div className="stat-header">
        <Shield size={16} color="var(--success)" />
        Mask Compliance
      </div>
      <div className="stat-value">{stats.mask_compliance_pct.toFixed(1)}%</div>
      <div className="stat-trend trend-up">Current Frame</div>
    </div>
    
    <div className="glass-card stat-card">
      <div className="stat-header">
        <Smile size={16} color="var(--warning)" />
        People Detected
      </div>
      <div className="stat-value">{stats.total_people}</div>
      <div className="stat-trend trend-down">Current Frame</div>
    </div>
  </div>
);

const EmotionChart = ({ emotions }) => (
  <div className="glass-panel chart-panel animate-slide-in" style={{ animationDelay: '0.2s' }}>
    <div className="panel-header">
      <div className="panel-title">
        <Activity size={20} color="var(--accent-primary)" />
        Live Emotion Trends
      </div>
    </div>
    <div style={{ width: '100%', height: 'calc(100% - 40px)' }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={emotions}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis dataKey="time" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
          <YAxis stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
          <Tooltip 
            contentStyle={{ backgroundColor: '#1a1d24', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
            itemStyle={{ color: '#fff' }}
          />
          <Line type="monotone" dataKey="happy" stroke="#10b981" strokeWidth={3} dot={false} activeDot={{ r: 6 }} isAnimationActive={false} />
          <Line type="monotone" dataKey="sad" stroke="#3b82f6" strokeWidth={2} dot={false} isAnimationActive={false} />
          <Line type="monotone" dataKey="angry" stroke="#ef4444" strokeWidth={2} dot={false} isAnimationActive={false} />
          <Line type="monotone" dataKey="fear" stroke="#8b5cf6" strokeWidth={2} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  </div>
);

const AlertList = ({ alerts }) => (
  <div className="glass-panel alerts-panel animate-slide-in" style={{ animationDelay: '0.3s' }}>
    <div className="panel-header">
      <div className="panel-title">
        <AlertTriangle size={20} color="var(--danger)" />
        Live Alerts
      </div>
      <div className="status-badge" style={{ background: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)', borderColor: 'rgba(239, 68, 68, 0.2)' }}>
        {alerts.length} Triggered
      </div>
    </div>
    <div className="alerts-list">
      {alerts.map(alert => (
        <div key={alert.id} className={`alert-item alert-${alert.type}`}>
          <div className="alert-content">
            <div className="alert-title">{alert.title}</div>
            <div className="alert-time">{alert.cam} • {alert.time}</div>
          </div>
        </div>
      ))}
    </div>
  </div>
);

// --- PLACEHOLDER VIEWS ---
const PlaceholderView = ({ title, icon: Icon, description }) => (
  <div className="glass-panel animate-slide-in" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', minHeight: '60vh', padding: '40px' }}>
    <Icon size={64} color="var(--accent-primary)" style={{ marginBottom: 24, opacity: 0.8 }} />
    <h2 style={{ fontSize: '1.8rem', marginBottom: '12px' }}>{title}</h2>
    <p style={{ color: 'var(--text-muted)', textAlign: 'center', maxWidth: '500px', lineHeight: '1.6' }}>{description}</p>
    <button style={{
      marginTop: '24px',
      padding: '10px 24px',
      background: 'rgba(255,255,255,0.05)',
      border: '1px solid var(--border-color)',
      color: '#fff',
      borderRadius: 'var(--radius-sm)',
      cursor: 'pointer',
      fontWeight: 500
    }}>
      Coming Soon
    </button>
  </div>
);

const CamerasView = () => <PlaceholderView title="Cameras Management" icon={Camera} description="Manage connected IP cameras, RSTP streams, and USB devices. View camera health and connection status." />;
const RecordingsView = () => <PlaceholderView title="Recordings & History" icon={Video} description="Browse, playback, and export historical video recordings and event snippets." />;
const AlertsRulesView = () => <PlaceholderView title="Alert Rules Engine" icon={AlertTriangle} description="Configure custom detection zones, confidence thresholds, and notification channels (Email, Telegram)." />;
const SettingsView = () => <PlaceholderView title="System Settings" icon={Settings} description="Configure system performance, model selection (YOLO11, RT-DETR), and hardware acceleration (GPU/CPU/MPS)." />;

// --- MAIN APP ---

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const { emotions, alerts, stats } = useTelemetry();

  return (
    <div className="app-container">
      {/* Sidebar */}
      <nav className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <Activity color="white" size={20} />
          </div>
          <div className="brand-title">LiveDetect</div>
        </div>
        
        <div className="nav-items">
          <a className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>
            <LayoutDashboard size={20} /> Dashboard
          </a>
          <a className={`nav-item ${activeTab === 'cameras' ? 'active' : ''}`} onClick={() => setActiveTab('cameras')}>
            <Camera size={20} /> Cameras
          </a>
          <a className={`nav-item ${activeTab === 'recordings' ? 'active' : ''}`} onClick={() => setActiveTab('recordings')}>
            <Video size={20} /> Recordings
          </a>
          <a className={`nav-item ${activeTab === 'alerts' ? 'active' : ''}`} onClick={() => setActiveTab('alerts')}>
            <AlertTriangle size={20} /> Alerts Rules
          </a>
          <div style={{ marginTop: 'auto', paddingTop: '40px' }}>
            <a className={`nav-item ${activeTab === 'settings' ? 'active' : ''}`} onClick={() => setActiveTab('settings')}>
              <Settings size={20} /> Settings
            </a>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="main-content">
        <header className="top-header">
          <div className="header-title">
            {activeTab === 'dashboard' && 'Overview'}
            {activeTab === 'cameras' && 'Cameras Management'}
            {activeTab === 'recordings' && 'Recordings & History'}
            {activeTab === 'alerts' && 'Alert Rules Configuration'}
            {activeTab === 'settings' && 'System Settings'}
          </div>
          <div className="header-actions">
            <div className="status-badge">
              <div className="status-dot"></div>
              System Active
            </div>
          </div>
        </header>

        {activeTab === 'dashboard' && (
          <div className="dashboard">
            {/* Left Column: Video & Stats */}
            <div className="main-feed">
              <VideoFeed />
              <StatsPanel stats={stats} />
            </div>

            {/* Right Column: Alerts & Charts */}
            <div className="side-panel">
              <AlertList alerts={alerts} />
              <EmotionChart emotions={emotions} />
            </div>
          </div>
        )}
        
        {activeTab === 'cameras' && <CamerasView />}
        {activeTab === 'recordings' && <RecordingsView />}
        {activeTab === 'alerts' && <AlertsRulesView />}
        {activeTab === 'settings' && <SettingsView />}
      </main>
    </div>
  );
}

export default App;
