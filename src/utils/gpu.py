"""GPU detection and information utilities.

All functions gracefully degrade when CUDA / PyTorch is unavailable,
returning safe defaults so callers never need to guard imports.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def is_gpu_available() -> bool:
    """Check whether a CUDA-capable GPU is available via PyTorch.

    Returns:
        ``True`` if ``torch.cuda.is_available()`` succeeds, ``False`` otherwise.
    """
    try:
        import torch  # type: ignore[import-untyped]
        return torch.cuda.is_available()
    except ImportError:
        logger.debug("PyTorch not installed – GPU unavailable")
        return False
    except Exception:
        logger.debug("Error checking GPU availability", exc_info=True)
        return False


def get_gpu_info() -> dict[str, Any]:
    """Return detailed information about the first CUDA device.

    Returns:
        A dict with keys ``available``, ``device_name``, ``device_count``,
        ``memory_total_mb``, ``memory_used_mb``, ``memory_free_mb``,
        ``cuda_version``, and ``cudnn_version``.  If no GPU is found every
        numeric field is ``0`` / ``None``.
    """
    info: dict[str, Any] = {
        "available": False,
        "device_name": None,
        "device_count": 0,
        "memory_total_mb": 0,
        "memory_used_mb": 0,
        "memory_free_mb": 0,
        "cuda_version": None,
        "cudnn_version": None,
    }

    try:
        import torch  # type: ignore[import-untyped]

        if not torch.cuda.is_available():
            return info

        info["available"] = True
        info["device_count"] = torch.cuda.device_count()
        info["device_name"] = torch.cuda.get_device_name(0)
        info["cuda_version"] = torch.version.cuda

        # Memory stats for device 0
        mem_total = torch.cuda.get_device_properties(0).total_mem
        mem_reserved = torch.cuda.memory_reserved(0)
        mem_allocated = torch.cuda.memory_allocated(0)
        info["memory_total_mb"] = round(mem_total / (1024 * 1024), 1)
        info["memory_used_mb"] = round(mem_allocated / (1024 * 1024), 1)
        info["memory_free_mb"] = round((mem_total - mem_reserved) / (1024 * 1024), 1)

        # cuDNN version
        if torch.backends.cudnn.is_available():
            info["cudnn_version"] = str(torch.backends.cudnn.version())

    except ImportError:
        logger.debug("PyTorch not installed – cannot query GPU info")
    except Exception:
        logger.warning("Failed to query GPU info", exc_info=True)

    return info


def get_optimal_device() -> str:
    """Return the optimal PyTorch device string for inference.

    Returns:
        ``'cuda:0'`` when a CUDA GPU is available, ``'mps'`` on Apple
        Silicon with PyTorch MPS support, otherwise ``'cpu'``.
    """
    try:
        import torch  # type: ignore[import-untyped]

        if torch.cuda.is_available():
            return "cuda:0"

        # Apple Silicon Metal Performance Shaders
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"

    except ImportError:
        pass
    except Exception:
        logger.debug("Error determining optimal device", exc_info=True)

    return "cpu"


def get_gpu_memory_usage() -> dict[str, Any] | None:
    """Return current GPU memory usage statistics.

    Returns:
        A dict with ``allocated_mb``, ``reserved_mb``, ``max_allocated_mb``,
        and ``utilization_pct`` for device 0, or ``None`` if unavailable.
    """
    try:
        import torch  # type: ignore[import-untyped]

        if not torch.cuda.is_available():
            return None

        allocated = torch.cuda.memory_allocated(0)
        reserved = torch.cuda.memory_reserved(0)
        max_allocated = torch.cuda.max_memory_allocated(0)
        total = torch.cuda.get_device_properties(0).total_mem

        utilization = (allocated / total * 100) if total > 0 else 0.0

        return {
            "allocated_mb": round(allocated / (1024 * 1024), 1),
            "reserved_mb": round(reserved / (1024 * 1024), 1),
            "max_allocated_mb": round(max_allocated / (1024 * 1024), 1),
            "total_mb": round(total / (1024 * 1024), 1),
            "utilization_pct": round(utilization, 1),
        }

    except ImportError:
        return None
    except Exception:
        logger.debug("Error reading GPU memory usage", exc_info=True)
        return None
