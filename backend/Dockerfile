# Build from the REPO ROOT:  docker build -f backend/Dockerfile -t aegis-backend .
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app LISTS_DIR=/app/lists

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/aegis ./aegis
COPY lists ./lists

# Train a baseline model at build so the image is self-sufficient (CPU, seconds).
RUN python -m aegis.train.train_model || true

EXPOSE 8000
CMD ["uvicorn", "aegis.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
