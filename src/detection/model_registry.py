import os
import structlog
from typing import Dict, Any, Optional
from ultralytics import YOLO

logger = structlog.get_logger()

class ModelRegistry:
    """
    Singleton registry to load and cache ML models in memory.
    Ensures we don't load the same weights multiple times.
    """
    _instance = None
    _models: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelRegistry, cls).__new__(cls)
        return cls._instance

    def get_yolo(self, model_path: str = "yolo11n.pt", device: str = "cpu") -> YOLO:
        """
        Get or load a YOLO model.
        
        Args:
            model_path: Path to the weights file (or standard Ultralytics name)
            device: Device to run inference on ('cpu', 'cuda:0', 'mps')
        """
        cache_key = f"yolo_{model_path}_{device}"
        
        if cache_key not in self._models:
            logger.info("loading_model", model=model_path, device=device)
            try:
                # Ensure the weights directory exists if we are downloading
                os.makedirs("models/weights", exist_ok=True)
                
                # Ultralytics auto-downloads to current directory if not found.
                # If it's a standard model, it will download. If local, it loads.
                model = YOLO(model_path)
                model.to(device)
                
                # Warmup the model with a dummy frame
                import numpy as np
                dummy = np.zeros((640, 640, 3), dtype=np.uint8)
                model.predict(dummy, verbose=False)
                
                self._models[cache_key] = model
                logger.info("model_loaded_successfully", model=model_path)
            except Exception as e:
                logger.error("failed_to_load_model", model=model_path, error=str(e))
                raise

        return self._models[cache_key]

# Global instance
registry = ModelRegistry()
