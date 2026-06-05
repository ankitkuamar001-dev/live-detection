import cv2
import threading
import time
import structlog
from typing import Optional, Tuple
import numpy as np

logger = structlog.get_logger()

class VideoStream:
    """
    Captures video from a camera source in a background thread.
    Always maintains the most recent frame to prevent buffer bloat and lag.
    """
    def __init__(self, source: int | str = 0, name: str = "webcam"):
        self.source = source
        self.name = name
        self.cap = cv2.VideoCapture(source)
        
        if not self.cap.isOpened():
            logger.error("camera_failed_to_open", source=source)
            raise RuntimeError(f"Failed to open video source {source}")
            
        # Get properties
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        logger.info("camera_opened", source=source, fps=self.fps, width=self.width, height=self.height)

        self.grabbed: bool = False
        self.frame: Optional[np.ndarray] = None
        self.stopped: bool = False
        self._lock = threading.Lock()
        
        # Start reading the first frame
        self.grabbed, self.frame = self.cap.read()

    def start(self) -> 'VideoStream':
        """Start the thread to read frames from the video stream."""
        self.stopped = False
        thread = threading.Thread(target=self._update, name=f"VideoStream-{self.name}", args=())
        thread.daemon = True
        thread.start()
        return self

    def _update(self) -> None:
        """Keep looping and reading the stream until stopped."""
        while not self.stopped:
            # If the source is a file, we might want to respect FPS, but for webcam we read as fast as possible
            grabbed, frame = self.cap.read()
            
            if not grabbed:
                logger.warning("camera_frame_drop", source=self.source)
                # If it's a file, it might have ended. For webcam, it might be a temporary glitch.
                if isinstance(self.source, str) and not str(self.source).startswith("rtsp"):
                    # End of video file
                    self.stop()
                    break
                time.sleep(0.01)
                continue

            with self._lock:
                self.grabbed = grabbed
                self.frame = frame

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Return the most recently read frame."""
        with self._lock:
            if self.frame is None:
                return self.grabbed, None
            return self.grabbed, self.frame.copy()

    def stop(self) -> None:
        """Stop the stream and release the camera."""
        self.stopped = True
        if self.cap.isOpened():
            self.cap.release()
        logger.info("camera_stopped", source=self.source)
