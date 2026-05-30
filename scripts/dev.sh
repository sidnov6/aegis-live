#!/usr/bin/env bash
# One-command local launch: backend (FastAPI) + frontend (Next.js dev).
# Usage: ./scripts/dev.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# --- backend venv -----------------------------------------------------------
if [ ! -d backend/.venv ]; then
  echo "[setup] creating backend venv…"
  python3 -m venv backend/.venv
  backend/.venv/bin/pip install --upgrade pip -q
  backend/.venv/bin/pip install -r backend/requirements.txt -q
fi

# --- seed sanctions list (offline-safe) + try a live refresh ----------------
echo "[lists] refreshing sanctions lists (falls back to seed if offline)…"
PYTHONPATH=backend backend/.venv/bin/python -m aegis.lists.refresh || true

# --- train model if missing -------------------------------------------------
if [ ! -f data/model_lgbm.txt ]; then
  echo "[train] no model found — training LightGBM + anomaly head…"
  PYTHONPATH=backend backend/.venv/bin/python -m aegis.train.train_model
fi

# --- UI deps ----------------------------------------------------------------
if [ ! -d ui/node_modules ]; then
  echo "[setup] installing UI deps…"
  (cd ui && npm install)
fi

# --- launch both ------------------------------------------------------------
echo "[run] starting backend on :8000 and UI on :3000"
PYTHONPATH=backend backend/.venv/bin/python -m uvicorn aegis.api.app:app \
  --host 0.0.0.0 --port 8000 &
BACK=$!
trap "kill $BACK 2>/dev/null || true" EXIT
(cd ui && npm run dev) &
FRONT=$!
trap "kill $BACK $FRONT 2>/dev/null || true" EXIT

echo ""
echo "  ┌────────────────────────────────────────────┐"
echo "  │  AEGIS Live                                  │"
echo "  │  Wall:   http://localhost:3000               │"
echo "  │  API:    http://localhost:8000/api/health    │"
echo "  └────────────────────────────────────────────┘"
wait
