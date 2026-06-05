"""Timing and FPS measurement utilities."""

from __future__ import annotations

import time
from collections import deque
from contextlib import contextmanager
from typing import Any, Generator


class Timer:
    """Context manager for timing code blocks.

    Usage::

        with Timer("inference") as t:
            result = model.predict(frame)
        print(f"Took {t.elapsed_ms:.1f}ms")
    """

    def __init__(self, name: str = "") -> None:
        self.name: str = name
        self.elapsed_ms: float = 0.0
        self._start: float = 0.0

    def __enter__(self) -> Timer:
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000

    def __repr__(self) -> str:
        return f"Timer(name={self.name!r}, elapsed_ms={self.elapsed_ms:.2f})"


class FPSCounter:
    """Rolling-window FPS counter.

    Maintains a fixed-size window of timestamps and computes the
    average frames-per-second over that window.

    Usage::

        fps_counter = FPSCounter(window_size=30)
        while capturing:
            frame = capture()
            current_fps = fps_counter.tick()
    """

    def __init__(self, window_size: int = 30) -> None:
        self._timestamps: deque[float] = deque(maxlen=window_size)

    def tick(self) -> float:
        """Record a new frame timestamp and return the current FPS."""
        self._timestamps.append(time.perf_counter())
        return self.fps

    @property
    def fps(self) -> float:
        """Calculate the average FPS from the rolling window."""
        if len(self._timestamps) < 2:
            return 0.0
        elapsed = self._timestamps[-1] - self._timestamps[0]
        if elapsed <= 0:
            return 0.0
        return (len(self._timestamps) - 1) / elapsed

    def reset(self) -> None:
        """Clear all recorded timestamps."""
        self._timestamps.clear()

    def __repr__(self) -> str:
        return f"FPSCounter(fps={self.fps:.1f}, samples={len(self._timestamps)})"


@contextmanager
def timed_block(name: str = "") -> Generator[Timer, None, None]:
    """Functional context-manager wrapper around :class:`Timer`.

    Usage::

        with timed_block("db_query") as t:
            rows = await db.fetch_all(query)
        logger.info("Query took %s ms", t.elapsed_ms)
    """
    timer = Timer(name)
    timer._start = time.perf_counter()
    try:
        yield timer
    finally:
        timer.elapsed_ms = (time.perf_counter() - timer._start) * 1000
