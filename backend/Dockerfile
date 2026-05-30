# Build from the REPO ROOT:  docker build -f backend/Dockerfile -t aegis-backend .
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app LISTS_DIR=/app/lists

# libgomp1 = LightGBM's OpenMP runtime (missing on slim); without it the model
# can't import/load and scoring silently degrades to the heuristic.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/aegis ./aegis
COPY lists ./lists

# Train + bake the models into the image (CPU, seconds). Non-fatal so a transient
# hiccup never breaks the image; with libgomp1 present this succeeds + loads.
RUN python -m aegis.train.train_model \
    && python -c "import lightgbm,joblib;lightgbm.Booster(model_file='data/model_lgbm.txt');joblib.load('data/anomaly_iforest.joblib');print('MODELS BAKED + LOADABLE')" \
    || echo "WARN: model bake failed at build; runtime will use heuristic fallback"

EXPOSE 8000
CMD ["uvicorn", "aegis.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
