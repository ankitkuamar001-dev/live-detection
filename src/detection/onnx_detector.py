"""
ONNX Runtime object detector — drop-in alternative to PyTorch ObjectDetector.

Uses ONNX Runtime with CPU or CUDA execution providers for faster inference.
Pre/post processing matches YOLO v8/v11 specification.

Usage::

    detector = OnnxDetector("models/weights/yolo11n.onnx")
    detections = detector.detect(frame)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np
import structlog

logger = structlog.get_logger(__name__)


class OnnxDetector:
    """YOLO detector using ONNX Runtime for inference."""

    def __init__(
        self,
        model_path: str,
        *,
        conf_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        imgsz: int = 640,
        device: str = "cpu",
    ) -> None:
        import onnxruntime as ort

        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.imgsz = imgsz

        # Select execution provider
        providers = ["CPUExecutionProvider"]
        if device != "cpu":
            available = ort.get_available_providers()
            if "CUDAExecutionProvider" in available:
                providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
                logger.info("onnx_using_cuda")
            else:
                logger.warning("onnx_cuda_not_available_falling_back_to_cpu")

        self.session = ort.InferenceSession(model_path, providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [o.name for o in self.session.get_outputs()]

        # Load COCO class names (default for YOLO)
        self.class_names = self._load_coco_names()

        logger.info(
            "onnx_detector_initialized",
            model=model_path,
            providers=providers,
            input_shape=self.session.get_inputs()[0].shape,
        )

    def _load_coco_names(self) -> dict[int, str]:
        """Load default COCO class names."""
        names = {
            0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 4: "airplane",
            5: "bus", 6: "train", 7: "truck", 8: "boat", 9: "traffic light",
            10: "fire hydrant", 11: "stop sign", 12: "parking meter", 13: "bench",
            14: "bird", 15: "cat", 16: "dog", 17: "horse", 18: "sheep", 19: "cow",
            20: "elephant", 21: "bear", 22: "zebra", 23: "giraffe", 24: "backpack",
            25: "umbrella", 26: "handbag", 27: "tie", 28: "suitcase", 29: "frisbee",
            30: "skis", 31: "snowboard", 32: "sports ball", 33: "kite", 34: "baseball bat",
            35: "baseball glove", 36: "skateboard", 37: "surfboard", 38: "tennis racket",
            39: "bottle", 40: "wine glass", 41: "cup", 42: "fork", 43: "knife",
            44: "spoon", 45: "bowl", 46: "banana", 47: "apple", 48: "sandwich",
            49: "orange", 50: "broccoli", 51: "carrot", 52: "hot dog", 53: "pizza",
            54: "donut", 55: "cake", 56: "chair", 57: "couch", 58: "potted plant",
            59: "bed", 60: "dining table", 61: "toilet", 62: "tv", 63: "laptop",
            64: "mouse", 65: "remote", 66: "keyboard", 67: "cell phone", 68: "microwave",
            69: "oven", 70: "toaster", 71: "sink", 72: "refrigerator", 73: "book",
            74: "clock", 75: "vase", 76: "scissors", 77: "teddy bear", 78: "hair drier",
            79: "toothbrush",
        }
        return names

    def _preprocess(self, frame: np.ndarray) -> tuple[np.ndarray, float, tuple[int, int]]:
        """Preprocess frame for YOLO ONNX input.

        Returns:
            (input_tensor, ratio, (pad_w, pad_h))
        """
        h, w = frame.shape[:2]
        scale = min(self.imgsz / h, self.imgsz / w)
        new_w, new_h = int(w * scale), int(h * scale)

        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # Pad to square
        pad_w = (self.imgsz - new_w) // 2
        pad_h = (self.imgsz - new_h) // 2
        padded = np.full((self.imgsz, self.imgsz, 3), 114, dtype=np.uint8)
        padded[pad_h:pad_h + new_h, pad_w:pad_w + new_w] = resized

        # HWC -> CHW, BGR -> RGB, normalize
        blob = padded[:, :, ::-1].transpose(2, 0, 1).astype(np.float32) / 255.0
        blob = np.expand_dims(blob, axis=0)

        return blob, scale, (pad_w, pad_h)

    def _postprocess(
        self,
        outputs: np.ndarray,
        scale: float,
        padding: tuple[int, int],
        orig_shape: tuple[int, int],
    ) -> list[dict[str, Any]]:
        """Post-process YOLO ONNX output into detection dicts."""
        # YOLO output: [1, num_classes+4, num_detections]
        predictions = outputs[0]  # shape: (1, 84, 8400) for COCO
        if predictions.ndim == 3:
            predictions = predictions[0]  # (84, 8400)
        predictions = predictions.T  # (8400, 84)

        # Split boxes and class scores
        boxes = predictions[:, :4]  # cx, cy, w, h
        scores = predictions[:, 4:]  # class scores

        # Get max class and confidence
        class_ids = np.argmax(scores, axis=1)
        confidences = scores[np.arange(len(scores)), class_ids]

        # Filter by confidence
        mask = confidences >= self.conf_threshold
        boxes = boxes[mask]
        class_ids = class_ids[mask]
        confidences = confidences[mask]

        if len(boxes) == 0:
            return []

        # Convert from cx, cy, w, h to x1, y1, x2, y2
        x1 = boxes[:, 0] - boxes[:, 2] / 2
        y1 = boxes[:, 1] - boxes[:, 3] / 2
        x2 = boxes[:, 0] + boxes[:, 2] / 2
        y2 = boxes[:, 1] + boxes[:, 3] / 2

        # Remove padding and rescale
        pad_w, pad_h = padding
        x1 = (x1 - pad_w) / scale
        y1 = (y1 - pad_h) / scale
        x2 = (x2 - pad_w) / scale
        y2 = (y2 - pad_h) / scale

        # Clip to image bounds
        oh, ow = orig_shape
        x1 = np.clip(x1, 0, ow)
        y1 = np.clip(y1, 0, oh)
        x2 = np.clip(x2, 0, ow)
        y2 = np.clip(y2, 0, oh)

        # NMS
        boxes_for_nms = np.stack([x1, y1, x2, y2], axis=1).tolist()
        indices = cv2.dnn.NMSBoxes(
            boxes_for_nms,
            confidences.tolist(),
            self.conf_threshold,
            self.iou_threshold,
        )

        detections = []
        if len(indices) > 0:
            indices = indices.flatten()
            for i in indices:
                cls_id = int(class_ids[i])
                detections.append({
                    "bbox": [int(x1[i]), int(y1[i]), int(x2[i]), int(y2[i])],
                    "confidence": float(confidences[i]),
                    "class_id": cls_id,
                    "class_name": self.class_names.get(cls_id, f"class_{cls_id}"),
                    "track_id": None,
                })

        return detections

    def detect(self, frame: np.ndarray) -> list[dict[str, Any]]:
        """Run ONNX inference on a single frame.

        Args:
            frame: BGR image (numpy array).

        Returns:
            List of detection dicts with bbox, confidence, class_name.
        """
        orig_shape = frame.shape[:2]
        blob, scale, padding = self._preprocess(frame)

        outputs = self.session.run(self.output_names, {self.input_name: blob})

        return self._postprocess(outputs[0], scale, padding, orig_shape)
