import cv2
import asyncio
import numpy as np
import structlog
from typing import AsyncGenerator
from src.video.stream import VideoStream
from src.pipeline.result import ObjectDetectionResult, BoundingBox
from src.detection.object_detector import ObjectDetector
from src.detection.mask_detector import MaskDetector
from src.detection.face_detector import FaceDetector
from src.detection.emotion_recognizer import EmotionRecognizer
from src.pipeline.quality import assess_frame_quality
from src.pipeline.enhancement import FastEnhancer, DeepEnhancer
from src.pipeline.temporal_filter import TemporalFilter
from src.alerts.dispatcher import AlertDispatcher
from src.api.routes.telemetry import broadcaster

logger = structlog.get_logger()

class PipelineProcessor:
    def __init__(
        self,
        detector: ObjectDetector,
        mask_detector: MaskDetector = None,
        event_logger=None,
        camera_id: str = "default",
    ):
        self.detector = detector
        self.mask_detector = mask_detector or MaskDetector()
        self.face_detector = FaceDetector()
        self.emotion_recognizer = EmotionRecognizer()
        self.emotion_filter = TemporalFilter(window_size=5)
        self.alert_dispatcher = AlertDispatcher(cooldown_seconds=60)
        self._event_logger = event_logger
        self._camera_id = camera_id

    def _cascade_mask_detection(self, frame: np.ndarray, detections: list):
        """
        Run mask detection only on cropped bounding boxes of people.
        Modifies the detections list in place.
        """
        for det in detections:
            if det["class_name"].lower() == "person":
                x1, y1, x2, y2 = det["bbox"]
                
                # Crop the person. Add a small margin if possible.
                h, w = frame.shape[:2]
                cx1 = max(0, x1 - 10)
                cy1 = max(0, y1 - 20)
                cx2 = min(w, x2 + 10)
                cy2 = min(h, y2 + 10)
                
                crop = frame[cy1:cy2, cx1:cx2]
                
                # Detect mask status
                status = self.mask_detector.detect_mask(crop, track_id=det.get("track_id"))
                det["mask_status"] = status
        return detections

    def _cascade_emotion_recognition(self, frame: np.ndarray, detections: list):
        """
        Run face detection and emotion recognition on cropped bounding boxes of people.
        """
        active_tracks = []
        for det in detections:
            track_id = det.get("track_id")
            if track_id is not None:
                active_tracks.append(track_id)
                
            if det["class_name"].lower() == "person":
                x1, y1, x2, y2 = det["bbox"]
                
                # Crop the person
                h, w = frame.shape[:2]
                cx1 = max(0, x1)
                cy1 = max(0, y1)
                cx2 = min(w, x2)
                cy2 = min(h, y2)
                person_crop = frame[cy1:cy2, cx1:cx2]
                
                # 1. MediaPipe Face Detection
                face_crop = self.face_detector.detect_face(person_crop)
                
                if face_crop is not None:
                    # 2. HSEmotion Recognition
                    emotion, confidence = self.emotion_recognizer.recognize(face_crop)
                    
                    if emotion and confidence >= 0.4:
                        # 3. Temporal Smoothing
                        smoothed_emotion = self.emotion_filter.update(track_id, emotion)
                        det["emotion"] = smoothed_emotion
                        det["emotion_confidence"] = confidence
                    else:
                        # Clear old history if below threshold to prevent stuck emotions
                        det["emotion"] = None
                        det["emotion_confidence"] = 0.0
                else:
                    det["emotion"] = None
                    det["emotion_confidence"] = 0.0
                    
        # Cleanup old tracks to prevent memory leak
        self.emotion_filter.cleanup(active_tracks)
        return detections

    async def stream_mjpeg(self, video_stream: VideoStream, target_fps: int = 15) -> AsyncGenerator[bytes, None]:
        """
        Reads frames from a VideoStream, runs object detection, and yields MJPEG frames.
        Automatically applies FastEnhancement if quality is poor.
        """
        frame_interval = 1.0 / target_fps
        
        try:
            while not video_stream.stopped:
                start_time = asyncio.get_event_loop().time()
                
                grabbed, frame = video_stream.read()
                if not grabbed or frame is None:
                    await asyncio.sleep(0.05)
                    continue

                loop = asyncio.get_running_loop()

                # Frame Quality Assessment
                quality = await loop.run_in_executor(None, assess_frame_quality, frame)
                
                # Apply Fast Enhancement if necessary
                if quality["is_low_contrast"] or quality["is_blurry"]:
                    # If blurry, sharpen. If low contrast, apply CLAHE.
                    frame = await loop.run_in_executor(None, FastEnhancer.enhance, frame, quality["is_low_contrast"], quality["is_blurry"], False)
                
                # Run inference
                detections = await loop.run_in_executor(None, self.detector.detect, frame)
                
                # Cascade emotion recognition
                detections = await loop.run_in_executor(None, self._cascade_emotion_recognition, frame, detections)
                
                # Cascade mask detection
                detections = await loop.run_in_executor(None, self._cascade_mask_detection, frame, detections)
                
                # Fire alerts asynchronously (non-blocking)
                alert_models = []
                for det in detections:
                    try:
                        alert_models.append(ObjectDetectionResult(
                            class_id=det["class_id"],
                            class_name=det["class_name"],
                            confidence=det["confidence"],
                            bbox=BoundingBox(
                                x_min=det["bbox"][0],
                                y_min=det["bbox"][1],
                                x_max=det["bbox"][2],
                                y_max=det["bbox"][3]
                            ),
                            track_id=det.get("track_id"),
                            mask_status=det.get("mask_status"),
                            emotion=det.get("emotion"),
                            emotion_confidence=det.get("emotion_confidence")
                        ))
                    except BaseException:
                        pass
                if alert_models:
                    asyncio.create_task(self.alert_dispatcher.process_detections(alert_models))
                    
                # Broadcast real-time telemetry
                total_people = sum(1 for d in detections if d.get("class_name", "").lower() == "person")
                total_masks = sum(1 for d in detections if d.get("mask_status") == "with_mask")
                
                emotions = {}
                for d in detections:
                    em = d.get("emotion")
                    if em:
                        emotions[em.lower()] = emotions.get(em.lower(), 0) + 1
                        
                stats = {
                    "total_detections": len(detections),
                    "total_people": total_people,
                    "mask_compliance_pct": (total_masks / total_people * 100) if total_people > 0 else 0,
                    "emotions": emotions
                }
                asyncio.create_task(broadcaster.broadcast_stats(stats))
                
                # Log detection events to database
                if self._event_logger and detections:
                    for det in detections:
                        cls = det.get("class_name", "").lower()
                        # Log person-level detections (mask + emotion)
                        if cls == "person":
                            mask_s = det.get("mask_status")
                            if mask_s:
                                self._event_logger.log_event(
                                    camera_id=self._camera_id,
                                    detection_type="mask",
                                    label=mask_s,
                                    confidence=det["confidence"],
                                    bbox={"x1": det["bbox"][0], "y1": det["bbox"][1],
                                           "x2": det["bbox"][2], "y2": det["bbox"][3]},
                                    track_id=det.get("track_id"),
                                )
                            emotion = det.get("emotion")
                            if emotion:
                                self._event_logger.log_event(
                                    camera_id=self._camera_id,
                                    detection_type="emotion",
                                    label=emotion.lower(),
                                    confidence=det.get("emotion_confidence", 0.0),
                                    bbox={"x1": det["bbox"][0], "y1": det["bbox"][1],
                                           "x2": det["bbox"][2], "y2": det["bbox"][3]},
                                    track_id=det.get("track_id"),
                                )
                        # Log other objects of interest
                        elif cls in ("phone", "laptop", "bag", "bottle", "backpack",
                                     "handbag", "suitcase", "knife", "scissors"):
                            self._event_logger.log_event(
                                camera_id=self._camera_id,
                                detection_type="object",
                                label=cls,
                                confidence=det["confidence"],
                                bbox={"x1": det["bbox"][0], "y1": det["bbox"][1],
                                       "x2": det["bbox"][2], "y2": det["bbox"][3]},
                                track_id=det.get("track_id"),
                            )
                
                # Annotate frame
                annotated = await loop.run_in_executor(None, self.detector.draw_detections, frame, detections)
                
                # Encode as JPEG
                success, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if not success:
                    continue
                    
                frame_bytes = buffer.tobytes()
                
                # Yield multipart boundary and image
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )

                # Maintain target FPS
                elapsed = asyncio.get_event_loop().time() - start_time
                sleep_time = max(0, frame_interval - elapsed)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    
        except asyncio.CancelledError:
            logger.info("mjpeg_stream_cancelled")
            raise
        finally:
            video_stream.stop()

    async def process_video_file(self, input_path: str, output_path: str, deep_enhance: bool = False) -> dict:
        """
        Process an offline video file and write an annotated output video.
        """
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video file: {input_path}")
            
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # If deep_enhance is true, resolution is doubled
        outscale = 2.0 if deep_enhance else 1.0
        out_width = int(width * outscale)
        out_height = int(height * outscale)
        
        # Output video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (out_width, out_height))
        
        frames_processed = 0
        loop = asyncio.get_running_loop()
        
        deep_enhancer = DeepEnhancer() if deep_enhance else None
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            # Deep Enhancement (Real-ESRGAN)
            if deep_enhance:
                frame = await loop.run_in_executor(None, deep_enhancer.enhance, frame, outscale)
                
            # Inference
            detections = await loop.run_in_executor(None, self.detector.detect, frame)
            
            # Cascade emotion recognition
            detections = await loop.run_in_executor(None, self._cascade_emotion_recognition, frame, detections)
            
            # Cascade mask detection
            detections = await loop.run_in_executor(None, self._cascade_mask_detection, frame, detections)
            
            # Fire alerts asynchronously (non-blocking)
            alert_models = []
            for det in detections:
                try:
                    alert_models.append(ObjectDetectionResult(
                        class_id=det["class_id"],
                        class_name=det["class_name"],
                        confidence=det["confidence"],
                        bbox=BoundingBox(
                            x_min=det["bbox"][0],
                            y_min=det["bbox"][1],
                            x_max=det["bbox"][2],
                            y_max=det["bbox"][3]
                        ),
                        track_id=det.get("track_id"),
                        mask_status=det.get("mask_status"),
                        emotion=det.get("emotion"),
                        emotion_confidence=det.get("emotion_confidence")
                    ))
                except BaseException:
                    pass
            if alert_models:
                asyncio.create_task(self.alert_dispatcher.process_detections(alert_models))
            
            annotated = await loop.run_in_executor(None, self.detector.draw_detections, frame, detections)
            
            out.write(annotated)
            frames_processed += 1
            
            # Yield event loop every few frames to prevent blocking
            if frames_processed % 10 == 0:
                await asyncio.sleep(0)
                
        cap.release()
        out.release()
        
        return {
            "processed_frames": frames_processed,
            "total_frames": total_frames,
            "output_path": output_path
        }
