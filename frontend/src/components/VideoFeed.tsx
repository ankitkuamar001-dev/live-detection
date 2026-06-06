import { useState, useEffect } from 'react';
import { Camera, Video, Activity } from 'lucide-react';
import { STREAM_URL, API_URL } from '../config';

export default function VideoFeed() {
  const [isLive, setIsLive] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [useDeepEnhance, setUseDeepEnhance] = useState(false);
  const [processedVideoUrl, setProcessedVideoUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Revoke blob URL on cleanup to prevent memory leak
  useEffect(() => {
    return () => {
      if (processedVideoUrl) URL.revokeObjectURL(processedVideoUrl);
    };
  }, [processedVideoUrl]);

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setProcessedVideoUrl(null);
    setIsLive(false);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(
        `${API_URL}/video/upload?deep_enhance=${useDeepEnhance}`,
        { method: 'POST', body: formData }
      );

      if (response.ok) {
        const blob = await response.blob();
        setProcessedVideoUrl(URL.createObjectURL(blob));
      } else {
        setError('Failed to process video. Please try again.');
      }
    } catch {
      setError('Error uploading video. Check that the backend is running.');
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
            src={STREAM_URL}
            alt="Live Stream"
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
            onError={() => { setIsLive(false); setError('Failed to connect to camera.'); }}
          />
        ) : processedVideoUrl ? (
          <video
            src={processedVideoUrl}
            controls
            autoPlay
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          />
        ) : (
          <div className="video-placeholder">
            {isUploading ? (
              <>
                <Activity className="spinner" size={48} />
                <h3>Processing Video…</h3>
                <p style={{ color: 'var(--text-muted)', marginTop: 8 }}>
                  {useDeepEnhance ? 'Applying Real-ESRGAN Super-Resolution' : 'Running YOLO11 Inference'}
                </p>
              </>
            ) : (
              <>
                <Camera size={48} color="var(--text-muted)" style={{ marginBottom: 16 }} />
                <h3>Camera Offline</h3>
                <p style={{ color: 'var(--text-muted)', marginTop: 8 }}>
                  Select an option below to start detection
                </p>
              </>
            )}
          </div>
        )}

        {/* Error Toast */}
        {error && (
          <div className="video-error">
            {error}
            <button onClick={() => setError(null)} style={{ marginLeft: 12, background: 'none', border: 'none', color: '#fff', cursor: 'pointer', fontWeight: 600 }}>✕</button>
          </div>
        )}

        {/* Live overlay */}
        {(isLive || processedVideoUrl) && (
          <div className="video-overlay">
            <div className="cam-label">
              <span>●</span> {isLive ? 'CAM 01 — Live Detection' : 'Uploaded Video Processing'}
            </div>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="video-controls">
        <button
          className={`btn ${isLive ? 'btn-danger' : 'btn-primary'}`}
          onClick={() => { setIsLive(!isLive); setProcessedVideoUrl(null); setError(null); }}
        >
          <Video size={18} /> {isLive ? 'Stop Camera' : 'Start Live Camera'}
        </button>

        <label className="btn btn-outline">
          <Camera size={18} /> Upload Video
          <input type="file" accept="video/*" style={{ display: 'none' }} onChange={handleUpload} disabled={isUploading} />
        </label>

        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={useDeepEnhance}
              onChange={(e) => setUseDeepEnhance(e.target.checked)}
              disabled={isUploading || isLive}
            />
            Use Real-ESRGAN
          </label>
        </div>
      </div>
    </div>
  );
}
