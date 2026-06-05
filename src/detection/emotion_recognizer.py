import cv2
import numpy as np
import structlog
from typing import Tuple, Optional

logger = structlog.get_logger()

class EmotionRecognizer:
    def __init__(self, model_name: str = 'enet_b0_8_best_vgaf', device: str = 'cpu'):
        self.device = device
        self.model_name = model_name
        self.model = None
        self._initialize()

    def _initialize(self):
        try:
            import torch
            
            # Temporary monkey-patch torch.load to force weights_only=False
            # for older models like enet_b0_8_best_vgaf.pt that use timm layers
            original_load = torch.load
            def custom_load(*args, **kwargs):
                kwargs['weights_only'] = False
                return original_load(*args, **kwargs)
            
            torch.load = custom_load
            try:
                from hsemotion.facial_emotions import HSEmotionRecognizer
                self.model = HSEmotionRecognizer(model_name=self.model_name, device=self.device)
                logger.info("hsemotion_model_initialized", model_name=self.model_name)
            finally:
                torch.load = original_load
                
        except ImportError:
            logger.error("hsemotion_not_installed")
        except Exception as e:
            logger.error("hsemotion_load_failed", error=str(e))

    def recognize(self, face_crop: np.ndarray) -> Tuple[Optional[str], float]:
        """
        Classifies the emotion of a face crop.
        Returns a tuple of (emotion_name, confidence).
        Emotions: Anger, Contempt, Disgust, Fear, Happiness, Neutral, Sadness, Surprise
        """
        if self.model is None or face_crop is None or face_crop.size == 0:
            return None, 0.0

        try:
            # hsemotion expects BGR image (OpenCV default)
            emotion, scores = self.model.predict_emotions(face_crop, logits=False)
            confidence = float(max(scores))
            return emotion, confidence
        except Exception as e:
            logger.error("emotion_recognition_failed", error=str(e))
            return None, 0.0
