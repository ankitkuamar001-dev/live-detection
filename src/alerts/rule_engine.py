import re
from typing import List, Dict, Any, Callable
from src.pipeline.result import ObjectDetectionResult

class AlertRule:
    def __init__(self, rule_id: str, description: str, condition: Callable[[ObjectDetectionResult], bool]):
        self.rule_id = rule_id
        self.description = description
        self.condition = condition

class AlertRuleEngine:
    """
    Evaluates a list of ObjectDetectionResults against predefined rules.
    """
    def __init__(self):
        self.rules: List[AlertRule] = []
        self._load_default_rules()

    def _load_default_rules(self):
        # 1. No Mask Detected
        self.rules.append(AlertRule(
            rule_id="no_mask_detected",
            description="Person detected without a mask.",
            condition=lambda det: det.mask_status == "without_mask"
        ))
        
        # 2. Incorrect Mask
        self.rules.append(AlertRule(
            rule_id="incorrect_mask",
            description="Person wearing mask incorrectly.",
            condition=lambda det: det.mask_status == "mask_weared_incorrect"
        ))
        
        # 3. Angry Emotion
        self.rules.append(AlertRule(
            rule_id="angry_emotion",
            description="Person exhibiting angry emotion.",
            condition=lambda det: det.emotion and det.emotion.lower() == "anger"
        ))
        
        # 4. Fear Emotion
        self.rules.append(AlertRule(
            rule_id="fear_emotion",
            description="Person exhibiting fear emotion.",
            condition=lambda det: det.emotion and det.emotion.lower() == "fear"
        ))

    def evaluate(self, detections: List[ObjectDetectionResult]) -> List[Dict[str, Any]]:
        """
        Evaluates detections and returns a list of triggered alerts.
        """
        triggered_alerts = []
        for det in detections:
            for rule in self.rules:
                if rule.condition(det):
                    triggered_alerts.append({
                        "rule_id": rule.rule_id,
                        "description": rule.description,
                        "track_id": det.track_id,
                        "class_name": det.class_name,
                        "confidence": det.confidence
                    })
        return triggered_alerts
