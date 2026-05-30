# Dockerfile for the Hugging Face Space (Docker SDK). Listens on 7860 (HF default).
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    LISTS_DIR=/app/lists \
    DATABASE_URL=sqlite:////tmp/aegis.db \
    DEMO_FALLBACK=true \
    ENABLE_BTC=true \
    ENABLE_EXCHANGE=true

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY aegis ./aegis
COPY lists ./lists

# Bake a baseline model so the Space is self-sufficient (CPU, seconds).
RUN python -m aegis.train.train_model || true

EXPOSE 7860
CMD ["uvicorn", "aegis.api.app:app", "--host", "0.0.0.0", "--port", "7860"]
