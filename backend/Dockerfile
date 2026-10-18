FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy HF_HOME=/opt/models/huggingface \
    SHIFT_SPEECH_MODEL_PATH=/opt/models/whisper \
    SHIFT_DATABASE_PATH=/data/shift.sqlite3 SHIFT_ENVIRONMENT=production \
    HF_HUB_DISABLE_TELEMETRY=1 OMP_NUM_THREADS=2
WORKDIR /app
RUN pip install --no-cache-dir uv==0.11.21
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --extra voice --no-dev --no-install-project
COPY app ./app
COPY migrations ./migrations
# Public, pinned model downloads only; never copy a private .env or AMD key.
RUN .venv/bin/python -m app.speech.prepare \
    && .venv/bin/python -c 'from huggingface_hub import snapshot_download; from app.rag.embeddings import MODEL, REVISION; snapshot_download(MODEL, revision=REVISION, allow_patterns=["*.json","*.txt","*.safetensors","1_Pooling/*"], token=False)'
RUN groupadd --gid 10001 shift && useradd --uid 10001 --gid shift --no-create-home shift \
    && mkdir /data && chown shift:shift /data
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
USER shift
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s \
    CMD ["/app/.venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4)"]
CMD ["/app/.venv/bin/python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
