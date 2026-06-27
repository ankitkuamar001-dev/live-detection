#!/usr/bin/env python3
"""
Benchmark script — compare PyTorch vs ONNX inference performance.

Usage::

    python scripts/benchmark.py --pytorch yolo11n.pt --onnx models/weights/yolo11n.onnx --frames 100
"""

import argparse
import statistics
import sys
import time
from pathlib import Path

import cv2
import numpy as np


def generate_test_frames(n: int, size: int = 640) -> list[np.ndarray]:
    """Generate N random test frames."""
    return [np.random.randint(0, 255, (size, size, 3), dtype=np.uint8) for _ in range(n)]


def benchmark_pytorch(model_path: str, frames: list[np.ndarray]) -> dict:
    """Benchmark PyTorch YOLO inference."""
    from ultralytics import YOLO

    model = YOLO(model_path)

    # Warmup
    for _ in range(5):
        model.predict(frames[0], verbose=False)

    latencies = []
    for frame in frames:
        t0 = time.perf_counter()
        model.predict(frame, verbose=False)
        latencies.append((time.perf_counter() - t0) * 1000)

    return _compute_stats(latencies, "PyTorch")


def benchmark_onnx(model_path: str, frames: list[np.ndarray]) -> dict:
    """Benchmark ONNX Runtime inference."""
    from src.detection.onnx_detector import OnnxDetector

    detector = OnnxDetector(model_path)

    # Warmup
    for _ in range(5):
        detector.detect(frames[0])

    latencies = []
    for frame in frames:
        t0 = time.perf_counter()
        detector.detect(frame)
        latencies.append((time.perf_counter() - t0) * 1000)

    return _compute_stats(latencies, "ONNX")


def _compute_stats(latencies: list[float], label: str) -> dict:
    """Compute latency statistics."""
    sorted_lat = sorted(latencies)
    return {
        "label": label,
        "frames": len(latencies),
        "avg_ms": round(statistics.mean(latencies), 2),
        "p50_ms": round(sorted_lat[len(sorted_lat) // 2], 2),
        "p95_ms": round(sorted_lat[int(len(sorted_lat) * 0.95)], 2),
        "p99_ms": round(sorted_lat[int(len(sorted_lat) * 0.99)], 2),
        "min_ms": round(min(latencies), 2),
        "max_ms": round(max(latencies), 2),
        "fps": round(1000 / statistics.mean(latencies), 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark PyTorch vs ONNX inference")
    parser.add_argument("--pytorch", type=str, default="yolo11n.pt")
    parser.add_argument("--onnx", type=str, default=None)
    parser.add_argument("--frames", type=int, default=100)
    parser.add_argument("--size", type=int, default=640)
    args = parser.parse_args()

    print(f"Generating {args.frames} test frames ({args.size}x{args.size})...")
    frames = generate_test_frames(args.frames, args.size)

    results = []

    # PyTorch benchmark
    if Path(args.pytorch).exists():
        print(f"\n{'='*60}")
        print(f"Benchmarking PyTorch: {args.pytorch}")
        print(f"{'='*60}")
        pt_stats = benchmark_pytorch(args.pytorch, frames)
        results.append(pt_stats)
        _print_stats(pt_stats)
    else:
        print(f"Skipping PyTorch: {args.pytorch} not found")

    # ONNX benchmark
    if args.onnx and Path(args.onnx).exists():
        print(f"\n{'='*60}")
        print(f"Benchmarking ONNX: {args.onnx}")
        print(f"{'='*60}")
        onnx_stats = benchmark_onnx(args.onnx, frames)
        results.append(onnx_stats)
        _print_stats(onnx_stats)
    elif args.onnx:
        print(f"Skipping ONNX: {args.onnx} not found")

    # Comparison
    if len(results) == 2:
        print(f"\n{'='*60}")
        print("COMPARISON")
        print(f"{'='*60}")
        speedup = results[0]["avg_ms"] / results[1]["avg_ms"]
        print(f"ONNX is {speedup:.2f}x {'faster' if speedup > 1 else 'slower'} than PyTorch")
        print(f"PyTorch FPS: {results[0]['fps']} | ONNX FPS: {results[1]['fps']}")


def _print_stats(stats: dict) -> None:
    """Pretty print benchmark stats."""
    print(f"  Frames:  {stats['frames']}")
    print(f"  Avg:     {stats['avg_ms']:.2f} ms")
    print(f"  P50:     {stats['p50_ms']:.2f} ms")
    print(f"  P95:     {stats['p95_ms']:.2f} ms")
    print(f"  P99:     {stats['p99_ms']:.2f} ms")
    print(f"  Min:     {stats['min_ms']:.2f} ms")
    print(f"  Max:     {stats['max_ms']:.2f} ms")
    print(f"  FPS:     {stats['fps']}")


if __name__ == "__main__":
    main()
