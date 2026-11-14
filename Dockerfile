# syntax=docker/dockerfile:1

# Note: Dockerfile does not support inline comments, so keep them on separate lines.
# Keep in sync with your local venv (python --version)
ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-slim AS base

# Use the CPU-only PyTorch build (~200 MB instead of ~2.5 GB of CUDA libraries).
# Override with --build-arg TORCH_INDEX_URL=... if you need GPU support.
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu

# HF_HOME replaces the deprecated TRANSFORMERS_CACHE variable
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/home/appuser/.cache/huggingface

WORKDIR /app

# Create an unprivileged user plus the dirs it must write to:
# the Hugging Face cache and /data for the SQLite database.
# Named volumes mounted there inherit this ownership on first use.
ARG UID=10001
RUN useradd --create-home --uid ${UID} appuser && \
    mkdir -p ${HF_HOME} /data && \
    chown -R appuser:appuser /home/appuser /data

# Install Python dependencies. The pip cache mount speeds up rebuilds,
# so do NOT combine it with --no-cache-dir.
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    pip install torch --index-url ${TORCH_INDEX_URL} && \
    pip install -r requirements.txt

# Copy the source code owned by the app user
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000

# Production entrypoint; compose.yaml overrides it with runserver for development
CMD ["gunicorn", "review_project.wsgi:application", "--bind=0.0.0.0:8000", "--workers=2"]