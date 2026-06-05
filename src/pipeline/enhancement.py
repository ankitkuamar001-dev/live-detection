import cv2
import numpy as np
import structlog
from typing import Optional

logger = structlog.get_logger()

class FastEnhancer:
    """
    Applies high-speed computer vision enhancements suitable for real-time video streaming.
    """
    @staticmethod
    def enhance(frame: np.ndarray, apply_clahe: bool = True, apply_sharpen: bool = True, apply_denoise: bool = False) -> np.ndarray:
        enhanced = frame.copy()
        
        # 1. Contrast Limited Adaptive Histogram Equalization (CLAHE)
        # Excellent for improving contrast in low-light conditions without washing out the image
        if apply_clahe:
            lab = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            cl = clahe.apply(l)
            limg = cv2.merge((cl, a, b))
            enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
            
        # 2. Denoising
        # Bilateral filter reduces noise while keeping edges sharp, but it's slightly slow.
        if apply_denoise:
            enhanced = cv2.bilateralFilter(enhanced, 9, 75, 75)
            
        # 3. Sharpening (Unsharp Masking)
        if apply_sharpen:
            gaussian = cv2.GaussianBlur(enhanced, (0, 0), 2.0)
            enhanced = cv2.addWeighted(enhanced, 1.5, gaussian, -0.5, 0)
            
        return enhanced

class DeepEnhancer:
    """
    Applies state-of-the-art super-resolution using Real-ESRGAN.
    Extremely computationally heavy; use only for offline batch processing or very small cropped regions.
    """
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DeepEnhancer, cls).__new__(cls)
        return cls._instance
        
    def _load_model(self):
        if self._model is not None:
            return
            
        logger.info("loading_realesrgan_model")
        try:
            from basicsr.archs.rrdbnet_arch import RRDBNet
            from realesrgan import RealESRGANer
            
            # Using RealESRGAN_x4plus for general images
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
            self._model = RealESRGANer(
                scale=4,
                model_path='https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth',
                model=model,
                tile=0,
                tile_pad=10,
                pre_pad=0,
                half=False  # Set to True if using modern NVIDIA GPU
            )
            logger.info("realesrgan_loaded_successfully")
        except ImportError as e:
            logger.error("realesrgan_not_installed", error=str(e))
            raise RuntimeError("Real-ESRGAN dependencies are not installed. Run: pip install realesrgan basicsr facexlib gfpgan")
            
    def enhance(self, frame: np.ndarray, outscale: float = 2.0) -> np.ndarray:
        """
        Enhance a frame using Real-ESRGAN.
        outscale dictates the final resolution multiplier (e.g. 2.0 means 2x upscale).
        """
        self._load_model()
        try:
            # The model returns the upscaled image and a boolean for success
            output, _ = self._model.enhance(frame, outscale=outscale)
            return output
        except Exception as e:
            logger.error("realesrgan_inference_failed", error=str(e))
            return frame
