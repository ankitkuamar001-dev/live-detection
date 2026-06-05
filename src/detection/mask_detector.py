import os
import cv2
import numpy as np
import urllib.request
import structlog
from src.detection.model_registry import registry

logger = structlog.get_logger()

class MaskDetector:
    def __init__(self, model_path: str = "models/yolo11n_mask.pt", device: str = "cpu"):
        self.device = device
        self.model_path = model_path
        self.model = None
        self.is_mock = False
        
        # Ensure models directory exists
        os.makedirs(os.path.dirname(model_path) if os.path.dirname(model_path) else "models", exist_ok=True)
        
        try:
            if not os.path.exists(self.model_path):
                logger.warning("mask_model_not_found", path=self.model_path, msg="Falling back to heuristic mock classifier until weights are provided.")
                self.is_mock = True
            else:
                self.model = registry.get_yolo(self.model_path, device)
        except Exception as e:
            logger.error("mask_model_load_failed", error=str(e))
            self.is_mock = True

    def detect_mask(self, person_crop: np.ndarray, track_id: int = None) -> str:
        """
        Takes a cropped image of a person (or face) and returns the mask status.
        Classes: 'with_mask', 'without_mask', 'mask_weared_incorrect'
        """
        if person_crop.size == 0:
            return "without_mask"
            
        if self.is_mock:
            # Mock implementation for demo purposes when weights aren't available.
            # We use the track_id to ensure the status remains consistent across frames for the same person!
            if track_id is not None:
                np.random.seed(track_id * 42)
                rand = np.random.random()
            else:
                rand = np.random.random()
                
            if rand > 0.6:
                return "with_mask"
            elif rand > 0.3:
                return "without_mask"
            else:
                return "mask_weared_incorrect"
                
        # Real YOLO inference
        try:
            results = self.model.predict(
                source=person_crop,
                conf=0.5,
                verbose=False,
                device=self.device
            )
            
            if len(results) > 0 and len(results[0].boxes) > 0:
                # Find the box with highest confidence
                boxes = results[0].boxes
                best_idx = int(boxes.conf.argmax().cpu().numpy())
                cls_id = int(boxes.cls[best_idx].cpu().numpy())
                class_name = self.model.names[cls_id]
                
                # Map to standard classes if the model uses different names
                name_lower = class_name.lower()
                if "incorrect" in name_lower or "bad" in name_lower:
                    return "mask_weared_incorrect"
                elif "without" in name_lower or "no" in name_lower:
                    return "without_mask"
                else:
                    return "with_mask"
                    
            return "without_mask"  # Default if nothing detected in crop
            
        except Exception as e:
            logger.error("mask_inference_error", error=str(e))
            return "without_mask"
