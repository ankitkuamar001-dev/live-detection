import time
import asyncio
import structlog
from typing import List, Dict, Any
from src.pipeline.result import ObjectDetectionResult
from src.alerts.rule_engine import AlertRuleEngine
from src.alerts.channels.telegram import TelegramChannel
from src.alerts.channels.email import EmailChannel
from src.api.routes.telemetry import broadcaster

logger = structlog.get_logger()

class AlertDispatcher:
    """
    Evaluates detections against rules and dispatches alerts to channels.
    Maintains a cooldown dictionary to prevent alert spam.
    """
    def __init__(self, cooldown_seconds: int = 60):
        self.cooldown_seconds = cooldown_seconds
        self.rule_engine = AlertRuleEngine()
        
        # Initialize channels
        self.channels = [
            TelegramChannel(),
            EmailChannel()
        ]
        
        # Dictionary mapping rule_id to the timestamp it was last triggered
        self.cooldown_state: Dict[str, float] = {}

    def is_on_cooldown(self, rule_id: str) -> bool:
        """
        Returns True if the rule_id has been triggered recently.
        """
        last_triggered = self.cooldown_state.get(rule_id, 0)
        current_time = time.time()
        
        if current_time - last_triggered < self.cooldown_seconds:
            return True
            
        return False

    def update_cooldown(self, rule_id: str):
        self.cooldown_state[rule_id] = time.time()

    async def _dispatch_alert(self, alert_data: Dict[str, Any]):
        """
        Sends the alert to all configured channels concurrently.
        """
        rule_id = alert_data["rule_id"]
        title = f"Live Detection Alert: {rule_id}"
        message = (
            f"Rule Triggered: {alert_data['description']}\n"
            f"Class: {alert_data['class_name']}\n"
            f"Track ID: {alert_data.get('track_id', 'Unknown')}\n"
            f"Confidence: {alert_data['confidence']:.2f}\n"
            f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        tasks = [channel.send_alert(title, message) for channel in self.channels]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("channel_dispatch_error", channel=type(self.channels[i]).__name__, error=str(result))

    async def process_detections(self, detections: List[ObjectDetectionResult]):
        """
        Evaluates detections and fires alerts if they are not on cooldown.
        This should be called as an asyncio background task.
        """
        if not detections:
            return
            
        triggered_alerts = self.rule_engine.evaluate(detections)
        
        for alert in triggered_alerts:
            rule_id = alert["rule_id"]
            
            # Check global cooldown for this specific rule
            if not self.is_on_cooldown(rule_id):
                # Put on cooldown immediately to prevent race conditions in same frame
                self.update_cooldown(rule_id)
                logger.info("alert_triggered", rule_id=rule_id, track_id=alert.get("track_id"))
                
                # Broadcast over WebSocket for frontend UI
                alert_copy = alert.copy()
                alert_copy["time"] = time.strftime('%H:%M:%S')
                alert_copy["cam"] = "Main Camera"
                alert_copy["type"] = "danger" if "mask" in rule_id or "angry" in rule_id else "warning"
                alert_copy["id"] = int(time.time() * 1000)
                alert_copy["title"] = rule_id.replace("_", " ").title()
                asyncio.create_task(broadcaster.broadcast_alert(alert_copy))
                
                # Dispatch to external channels asynchronously
                asyncio.create_task(self._dispatch_alert(alert))
