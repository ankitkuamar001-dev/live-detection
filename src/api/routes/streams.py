import asyncio
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from src.video.stream import VideoStream
from src.pipeline.processor import PipelineProcessor
from src.detection.object_detector import ObjectDetector

router = APIRouter()

# Global instances for the demo
detector = ObjectDetector(model_path="yolo11n.pt", device="cpu")
pipeline = PipelineProcessor(detector=detector)
active_streams = {}

@router.get("/video/live")
async def get_live_video(request: Request):
    """
    Returns a multipart MJPEG stream from the webcam.
    """
    if "webcam" not in active_streams:
        # Start a new webcam stream
        try:
            vs = VideoStream(source=0, name="webcam").start()
            active_streams["webcam"] = vs
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Cannot open webcam: {str(e)}")

    vs = active_streams["webcam"]

    # We need to handle disconnects to avoid memory leaks.
    # FastAPI's StreamingResponse doesn't natively handle cleanup easily unless we use a background task
    # or watch for request.is_disconnected().
    
    async def event_generator():
        try:
            async for frame in pipeline.stream_mjpeg(vs, target_fps=15):
                if await request.is_disconnected():
                    break
                yield frame
        finally:
            # Stop the camera if this was the last client (simplified logic: just stop it for now)
            vs.stop()
            if "webcam" in active_streams:
                del active_streams["webcam"]

    return StreamingResponse(
        event_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
