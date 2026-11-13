ARG PYTHON_VERSION=3.11.8
FROM python:${PYTHON_VERSION}-slim AS base

ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    XDG_CACHE_HOME=/home/appuser/.cache \
    HF_HOME=/home/appuser/.cache/huggingface

WORKDIR /app

ARG UID=10001
RUN useradd --create-home --uid ${UID} appuser && \
    mkdir -p ${HF_HOME} && \
    chown -R appuser:appuser /home/appuser

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev && \
    rm -rf /var/lib/apt/lists/*


RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    pip install torch --index-url ${TORCH_INDEX_URL} && \
    pip install -r requirements.txt

COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000

CMD ["gunicorn", "review_project.wsgi:application", "--bind=0.0.0.0:8000", "--workers=2"]