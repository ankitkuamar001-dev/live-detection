import cv2
import numpy as np
from typing import Dict, Any

def assess_frame_quality(frame: np.ndarray) -> Dict[str, Any]:
    """
    Analyzes a frame to determine if it is blurry, low contrast, or poorly exposed.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Blur detection using variance of Laplacian
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
    is_blurry = blur_score < 100.0  # Threshold can be tuned

    # Contrast and brightness using histogram
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    pixels = gray.size
    
    # Percentage of dark and bright pixels
    dark_pixels = np.sum(hist[:50]) / pixels
    bright_pixels = np.sum(hist[205:]) / pixels
    
    is_low_contrast = (dark_pixels + bright_pixels) < 0.1
    is_dark = dark_pixels > 0.6
    
    return {
        "blur_score": float(blur_score),
        "is_blurry": bool(is_blurry),
        "is_low_contrast": bool(is_low_contrast),
        "is_dark": bool(is_dark)
    }
