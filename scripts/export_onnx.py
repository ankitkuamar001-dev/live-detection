#!/usr/bin/env python3
"""
Export YOLO model to ONNX format.

Usage::

    python scripts/export_onnx.py --model yolo11n.pt --output models/weights/yolo11n.onnx
    python scripts/export_onnx.py --model yolo11n.pt --half  # FP16
"""

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export YOLO model to ONNX")
    parser.add_argument("--model", type=str, default="yolo11n.pt", help="Path to YOLO .pt model")
    parser.add_argument("--output", type=str, default=None, help="Output ONNX path")
    parser.add_argument("--imgsz", type=int, default=640, help="Input image size")
    parser.add_argument("--opset", type=int, default=17, help="ONNX opset version")
    parser.add_argument("--half", action="store_true", help="FP16 quantization")
    parser.add_argument("--simplify", action="store_true", default=True, help="Simplify ONNX graph")
    parser.add_argument("--dynamic", action="store_true", default=True, help="Dynamic batch size")
    args = parser.parse_args()

    try:
        from ultralytics import YOLO
    except ImportError:
        print("Error: ultralytics not installed. Run: pip install ultralytics")
        sys.exit(1)

    model_path = Path(args.model)
    if not model_path.exists():
        print(f"Error: Model not found: {model_path}")
        sys.exit(1)

    print(f"Loading model: {model_path}")
    model = YOLO(str(model_path))

    print(f"Exporting to ONNX (opset={args.opset}, imgsz={args.imgsz}, half={args.half})")
    export_path = model.export(
        format="onnx",
        imgsz=args.imgsz,
        opset=args.opset,
        simplify=args.simplify,
        half=args.half,
        dynamic=args.dynamic,
    )

    if args.output:
        import shutil
        shutil.move(export_path, args.output)
        export_path = args.output

    print(f"\n✅ ONNX model exported to: {export_path}")
    print(f"   Size: {Path(export_path).stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
