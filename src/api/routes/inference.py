import os
import time
import aiofiles
import uuid
import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from src.pipeline.processor import PipelineProcessor
from src.detection.object_detector import ObjectDetector
from src.pipeline.result import FrameInferenceResult, ObjectDetectionResult, BoundingBox

router = APIRouter()

# Directories for uploads and outputs
UPLOAD_DIR = "data/uploads"
OUTPUT_DIR = "data/outputs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Global instance for demo
detector = ObjectDetector(model_path="yolo11n.pt", device="cpu")
pipeline = PipelineProcessor(detector=detector)

@router.post("/video/upload")
async def process_uploaded_video(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    deep_enhance: bool = False
):
    """
    Process an uploaded video file offline.
    If deep_enhance is true, applies Real-ESRGAN to every frame.
    """
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="File must be a video.")

    # Create temporary paths
    file_id = str(uuid.uuid4())
    input_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    output_path = os.path.join(OUTPUT_DIR, f"processed_{file_id}_{file.filename}")

    # Save uploaded file
    async with aiofiles.open(input_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)

    # Process offline
    # In production, we should offload this to Celery/Redis queue
    # For now, we block on await so we can return the processed file directly
    try:
        result = await pipeline.process_video_file(input_path, output_path, deep_enhance=deep_enhance)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process video: {str(e)}")
        
    # In a real app we'd return a URL and let the user stream it.
    # For simplicity, we return the file directly here if it's not too huge.
    return FileResponse(
        path=output_path,
        media_type="video/mp4",
        filename=f"processed_{file.filename}"
    )

@router.post("/detect", response_model=FrameInferenceResult)
async def detect_image(file: UploadFile = File(...)):
    """
    Run object detection on a single uploaded image and return JSON results.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    content = await file.read()
    nparr = np.frombuffer(content, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if frame is None:
        raise HTTPException(status_code=400, detail="Invalid image file.")

    start_time = time.time()
    raw_detections = detector.detect(frame)
    latency = (time.time() - start_time) * 1000

    results = []
    for det in raw_detections:
        x1, y1, x2, y2 = det["bbox"]
        results.append(
            ObjectDetectionResult(
                class_id=det["class_id"],
                class_name=det["class_name"],
                confidence=det["confidence"],
                bbox=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)
            )
        )

    return FrameInferenceResult(
        camera_id="upload",
        timestamp=time.time(),
        detections=results,
        latency_ms=latency
    )
