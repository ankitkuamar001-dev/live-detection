import cv2
import numpy as np
import structlog
from typing import Optional, Tuple

logger = structlog.get_logger()

class FaceDetector:
    def __init__(self, min_detection_confidence: float = 0.5):
        self.min_detection_confidence = min_detection_confidence
        self.face_detection = None
        self._initialize()
        
    def _initialize(self):
        try:
            import mediapipe as mp
            self.mp_face_detection = mp.solutions.face_detection
            self.face_detection = self.mp_face_detection.FaceDetection(
                model_selection=0, # 0 for close-range (within 2m), 1 for full-range
                min_detection_confidence=self.min_detection_confidence
            )
            logger.info("mediapipe_face_detector_initialized")
        except ImportError:
            logger.error("mediapipe_not_installed")

    def detect_face(self, person_crop: np.ndarray) -> Optional[np.ndarray]:
        """
        Takes a BGR image crop of a person and returns just the face crop.
        Returns None if no face is found.
        """
        if self.face_detection is None or person_crop is None or person_crop.size == 0:
            return None
            
        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)
        results = self.face_detection.process(rgb_image)
        
        if not results.detections:
            return None
            
        # Get highest confidence face
        best_detection = max(results.detections, key=lambda d: d.score[0])
        bboxC = best_detection.location_data.relative_bounding_box
        
        ih, iw, _ = person_crop.shape
        
        # Calculate pixel coordinates (with some margin)
        margin = 0.2 # 20% margin
        x = int(bboxC.xmin * iw)
        y = int(bboxC.ymin * ih)
        w = int(bboxC.width * iw)
        h = int(bboxC.height * ih)
        
        cx1 = max(0, int(x - w * margin))
        cy1 = max(0, int(y - h * margin))
        cx2 = min(iw, int(x + w + w * margin))
        cy2 = min(ih, int(y + h + h * margin))
        
        face_crop = person_crop[cy1:cy2, cx1:cx2]
        
        if face_crop.size == 0:
            return None
            
        return face_crop
