"""Prometheus metrics middleware setup.

Instruments the FastAPI application with request/response metrics
and exposes a ``/metrics`` endpoint for Prometheus scraping.
If ``prometheus-fastapi-instrumentator`` is not installed the setup
is silently skipped.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

logger = logging.getLogger(__name__)


def setup_metrics(app: FastAPI) -> None:
    """Attach Prometheus instrumentation to the FastAPI application.

    The middleware tracks:
    - Request counts and latencies by method / path / status.
    - In-progress request gauge.

    Args:
        app: The FastAPI application instance.
    """
    try:
        from prometheus_fastapi_instrumentator import Instrumentator  # type: ignore[import-untyped]

        Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            should_instrument_requests_inprogress=True,
            excluded_handlers=["/metrics"],
        ).instrument(app).expose(
            app,
            endpoint="/metrics",
            include_in_schema=True,
            tags=["Monitoring"],
        )
        logger.info("Prometheus metrics enabled at /metrics")
    except ImportError:
        logger.debug(
            "prometheus-fastapi-instrumentator not installed – metrics disabled"
        )
