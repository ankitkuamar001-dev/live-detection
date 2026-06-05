import asyncio
import json
import time
from typing import List, Dict, Any
from collections import deque
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog

logger = structlog.get_logger()
router = APIRouter()

class TelemetryBroadcaster:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        # In-memory history for charts (e.g. max 60 points)
        self.emotion_history: deque = deque(maxlen=60)
        self.recent_alerts: deque = deque(maxlen=20)
        
        # Initialize with some empty history
        for i in range(5):
            self._add_empty_history_point()

    def _add_empty_history_point(self):
        t = time.strftime('%H:%M:%S')
        self.emotion_history.append({"time": t, "happy": 0, "neutral": 0, "sad": 0, "angry": 0, "fear": 0})

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("telemetry_client_connected", clients=len(self.active_connections))
        
        # Send initial history state to the new client
        await self._send_to_client(websocket, {
            "type": "init",
            "emotions": list(self.emotion_history),
            "alerts": list(self.recent_alerts)
        })

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("telemetry_client_disconnected", clients=len(self.active_connections))

    async def broadcast_stats(self, stats: Dict[str, Any]):
        """
        Broadcasts real-time detection stats and updates history.
        """
        # 1. Update Emotion History
        t = time.strftime('%H:%M:%S')
        em_counts = stats.get("emotions", {})
        
        # Simplify mapping for the chart
        history_point = {
            "time": t,
            "happy": em_counts.get("happiness", 0),
            "neutral": em_counts.get("neutral", 0),
            "sad": em_counts.get("sadness", 0),
            "angry": em_counts.get("anger", 0),
            "fear": em_counts.get("fear", 0)
        }
        
        # Only add a new point every ~5 seconds to prevent the chart from moving too fast,
        # or we just aggregate. For simplicity, we just append every frame but that's 30fps.
        # Let's throttle history appending to once per second
        if len(self.emotion_history) == 0 or self.emotion_history[-1]["time"] != t:
            self.emotion_history.append(history_point)
            
        payload = {
            "type": "stats",
            "stats": stats,
            "emotions": list(self.emotion_history)
        }
        await self._broadcast(payload)

    async def broadcast_alert(self, alert: Dict[str, Any]):
        """
        Broadcasts a new alert and stores it in recent history.
        """
        self.recent_alerts.appendleft(alert)
        payload = {
            "type": "alert",
            "alert": alert
        }
        await self._broadcast(payload)

    async def _broadcast(self, message: dict):
        if not self.active_connections:
            return
            
        json_msg = json.dumps(message)
        dead_connections = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(json_msg)
            except Exception:
                dead_connections.append(connection)
                
        for dc in dead_connections:
            self.disconnect(dc)
            
    async def _send_to_client(self, websocket: WebSocket, message: dict):
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error("send_to_client_failed", error=str(e))

# Global instance
broadcaster = TelemetryBroadcaster()

@router.websocket("/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await broadcaster.connect(websocket)
    try:
        while True:
            # Keep connection alive, wait for client disconnect
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        broadcaster.disconnect(websocket)
    except Exception as e:
        logger.error("websocket_error", error=str(e))
        broadcaster.disconnect(websocket)
