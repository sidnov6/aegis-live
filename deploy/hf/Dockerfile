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

# libgomp1 is required by LightGBM (OpenMP runtime). Without it `import lightgbm`
# fails and the scorer silently falls back to the heuristic — i.e. no real ML.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY aegis ./aegis
COPY lists ./lists

# Train + bake the models into the image. Kept non-fatal so a transient hiccup
# never takes the Space down; with libgomp1 present this succeeds and the booster
# loads at runtime (verified via /api/health: model_loaded=true).
RUN python -m aegis.train.train_model \
    && python -c "import lightgbm,joblib;lightgbm.Booster(model_file='data/model_lgbm.txt');joblib.load('data/anomaly_iforest.joblib');print('MODELS BAKED + LOADABLE')" \
    || echo "WARN: model bake failed at build; runtime will use heuristic fallback"

EXPOSE 7860
CMD ["uvicorn", "aegis.api.app:app", "--host", "0.0.0.0", "--port", "7860"]
