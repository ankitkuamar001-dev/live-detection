import cv2
import numpy as np
from typing import List, Dict, Any, Tuple
import structlog
from src.detection.model_registry import registry

logger = structlog.get_logger()

class ObjectDetector:
    def __init__(self, model_path: str = "yolo11n.pt", device: str = "cpu", conf_threshold: float = 0.5):
        self.model = registry.get_yolo(model_path, device)
        self.conf_threshold = conf_threshold
        self.class_names = self.model.names
        self.track_history = {} # Maps track_id to a list of center points

    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Run inference and tracking on a single frame.
        Returns a list of detections with bounding boxes, classes, and track IDs.
        """
        # YOLO track uses ByteTrack by default if tracker="bytetrack.yaml" is provided.
        results = self.model.track(
            source=frame,
            conf=self.conf_threshold,
            persist=True,
            tracker="bytetrack.yaml",
            verbose=False,
            device=self.model.device
        )
        
        detections = []
        if len(results) > 0:
            boxes = results[0].boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                conf = float(box.conf[0].cpu().numpy())
                cls_id = int(box.cls[0].cpu().numpy())
                cls_name = self.class_names[cls_id]
                
                track_id = int(box.id[0].cpu().numpy()) if box.id is not None else None
                
                # Update track history for visual trails
                if track_id is not None:
                    cx = int((x1 + x2) / 2)
                    cy = int((y1 + y2) / 2)
                    if track_id not in self.track_history:
                        self.track_history[track_id] = []
                    self.track_history[track_id].append((cx, cy))
                    # Keep only last 30 points (approx 1 second at 30fps)
                    if len(self.track_history[track_id]) > 30:
                        self.track_history[track_id].pop(0)
                
                detections.append({
                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    "confidence": conf,
                    "class_id": cls_id,
                    "class_name": cls_name,
                    "track_id": track_id
                })
                
        # Cleanup stale track histories
        if len(results) > 0:
            current_ids = [int(box.id[0].cpu().numpy()) for box in results[0].boxes if box.id is not None]
            stale_ids = [tid for tid in self.track_history.keys() if tid not in current_ids]
            for tid in stale_ids:
                del self.track_history[tid]
                
        return detections

    def draw_detections(self, frame: np.ndarray, detections: List[Dict[str, Any]]) -> np.ndarray:
        """
        Draw bounding boxes and labels on the frame, and add an object count overlay.
        """
        annotated = frame.copy()
        counts = {}
        
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            track_id_str = f" #{det['track_id']}" if det.get("track_id") is not None else ""
            label = f"{det['class_name']}{track_id_str} {det['confidence']:.2f}"
            
            # Count objects
            cls_name = det['class_name']
            counts[cls_name] = counts.get(cls_name, 0) + 1
            
            # Use a unique color based on track_id if available, otherwise green
            if det.get("track_id") is not None:
                np.random.seed(det["track_id"] * 100)
                color = tuple([int(c) for c in np.random.randint(0, 255, size=3)])
                
                # Draw Visual Tracking Path (Trail)
                tid = det["track_id"]
                if tid in self.track_history and len(self.track_history[tid]) > 1:
                    points = np.array(self.track_history[tid], dtype=np.int32)
                    cv2.polylines(annotated, [points], isClosed=False, color=color, thickness=2)
            else:
                color = (0, 255, 0)
            
            # Draw box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # Draw label background
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(annotated, (x1, y1 - 20), (x1 + w, y1), color, -1)
            
            # Draw text
            cv2.putText(annotated, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            
        # Draw Object Counts Overlay
        if counts:
            y_offset = 30
            # Draw a semi-transparent background box for counts
            overlay = annotated.copy()
            cv2.rectangle(overlay, (10, 10), (200, 20 + len(counts) * 25), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.6, annotated, 0.4, 0, annotated)
            
            # Draw text for each count
            for cls_name, count in counts.items():
                text = f"{cls_name.capitalize()}: {count}"
                cv2.putText(annotated, text, (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                y_offset += 25
                
        # Draw Mask & Emotion Badges
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            y_badge = y2 + 20
            
            # Mask Status
            mask_status = det.get("mask_status")
            if mask_status:
                if mask_status == "with_mask":
                    m_color = (0, 255, 0)
                    m_text = "MASK OK"
                elif mask_status == "without_mask":
                    m_color = (0, 0, 255)
                    m_text = "NO MASK"
                else:
                    m_color = (0, 165, 255) # Orange
                    m_text = "INCORRECT MASK"
                    
                cv2.putText(annotated, m_text, (x1, y_badge), cv2.FONT_HERSHEY_SIMPLEX, 0.6, m_color, 2)
                y_badge += 20
                
            # Emotion Status
            emotion = det.get("emotion")
            if emotion:
                # Map emotions to emojis or colors
                em_color = (255, 0, 255) # Magenta for emotion
                conf = det.get("emotion_confidence", 0.0)
                e_text = f"Feel: {emotion.capitalize()} ({conf:.2f})"
                cv2.putText(annotated, e_text, (x1, y_badge), cv2.FONT_HERSHEY_SIMPLEX, 0.6, em_color, 2)
                
        return annotated

