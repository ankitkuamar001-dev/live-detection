# ── Stage 1: Builder ─────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specification
COPY pyproject.toml ./

# Install Python packages into a virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -e ".[dev]" || true

# Copy source code and install the package
COPY . .
RUN pip install --no-cache-dir -e .


# ── Stage 2: Runtime ─────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# System dependencies for OpenCV, MediaPipe
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application source
COPY src/ ./src/
COPY configs/ ./configs/
COPY Makefile ./
COPY pyproject.toml ./

# Copy model weights (if present)
COPY models/ ./models/ 2>/dev/null || true
COPY yolo11n.pt ./yolo11n.pt 2>/dev/null || true

# Create data directories
RUN mkdir -p data/snapshots data/clips data/recordings

# Environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production

# Expose FastAPI port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/ || exit 1

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
