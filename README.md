# AEGIS Live — Real-Time Streaming AML Detection
### Codename `STROMWACHE` · Free-tier · Real-time · Finance-only

A live wall of real cryptocurrency transactions streaming onto your screen, each
scored for money-laundering risk **the instant it arrives**. The ticker moves, the
throughput counter climbs, the network graph grows, and when a transaction touches
the dirty corners of the network it lights up red in real time — with the reason
and the subgraph behind it, plus an auto-drafted SAR.

> **The honest frame:** live data never carries a "laundered: yes/no" label —
> laundering is confirmed retrospectively. So AEGIS does what every real
> production AML system does: it **scores in real time, and humans confirm later.**
> Live red flags are **predictions**, except sanctions exact-hits, which are
> ground-truth designations.

---

## What's in the box (all 14 parts of the blueprint, built)

| Layer | Module | Status |
|---|---|---|
| Resilient WS ingestion (BTC mempool + Binance ticker, +optional ETH) | `aegis/ingestion/` | ✅ |
| Event bus w/ bounded queue, drop-oldest backpressure, load sampling | `aegis/stream/bus.py` | ✅ |
| Sliding-window in-memory transaction graph (NetworkX) | `aegis/stream/rolling_graph.py` | ✅ |
| Live feature builder w/ strict train↔live parity | `aegis/stream/features.py` | ✅ |
| Sanctions / known-illicit screening (exact + N-hop) | `aegis/scoring/sanctions.py` | ✅ |
| LightGBM model inference (+heuristic fallback) | `aegis/scoring/model.py` | ✅ |
| Structural anomaly (IsolationForest +streaming-z fallback) | `aegis/scoring/anomaly.py` | ✅ |
| Ensemble + human-readable reason | `aegis/scoring/ensemble.py` | ✅ |
| Alert engine: threshold + dedup + rate-limit | `aegis/alerting/engine.py` | ✅ |
| Subgraph explanation | `aegis/alerting/explain.py` | ✅ |
| LLM SAR drafting (LiteLLM; template fallback) | `aegis/alerting/sar.py` | ✅ |
| Offline training on synthetic-AMLSim/Elliptic (MLflow-ready) | `aegis/train/train_model.py` | ✅ |
| Eval / CI gates (parity, latency, detection) | `aegis/eval/gates.py` | ✅ |
| FastAPI + WebSocket push | `aegis/api/` | ✅ |
| Next.js Surveillance Wall (Wall · Graph · Alerts · Case/SAR · Health) | `ui/` | ✅ |
| Nightly OFAC list refresh | `aegis/lists/refresh.py` + GH Action | ✅ |

---

## Run it locally (one command)

```bash
./scripts/dev.sh
```

This creates the Python venv, refreshes sanctions lists (falls back to the bundled
seed offline), trains a baseline model, installs UI deps, and launches:

- **Wall:** http://localhost:3000
- **API:** http://localhost:8000/api/health

### Or with Docker

```bash
docker compose up --build
# Wall: http://localhost:3000   API: http://localhost:8000
```

### Manual / piecemeal

```bash
# backend
python3 -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements.txt
PYTHONPATH=backend backend/.venv/bin/python -m aegis.lists.refresh     # sanctions lists
PYTHONPATH=backend backend/.venv/bin/python -m aegis.train.train_model # train model
PYTHONPATH=backend backend/.venv/bin/python -m uvicorn aegis.api.app:app --port 8000

# frontend
cd ui && npm install && npm run dev
```

> **Live feeds vs. demo fallback:** by default the backend connects to the real
> BTC mempool + Binance trade stream (free, keyless). On a locked-down network
> (corporate TLS interception, no egress) those WebSockets may fail — after an 8s
> grace period a built-in synthetic source takes over so the wall always has
> motion, including occasional sanctioned-address hits for the red-bloom. Real
> feeds always take priority. The Health tab shows exactly which feeds are live.

---

## The five screens

1. **The Wall** — live transaction stream stamped with a verdict + latency as each
   lands; moving price ticker; throughput / scored / flagged / sanctioned / alerts
   / p95-latency counters; live mini network graph.
2. **Network Graph** — the rolling tx graph (force-directed canvas); nodes appear
   and age out; sanctioned nodes ring red with directional particles.
3. **Alert Console** — ranked live alert queue with reason + triggering subgraph.
4. **Case / SAR** — the explained subgraph + drafted SAR with Approve / File / Dismiss.
5. **Stream Health** — feeds, throughput, latency p50/p95/p99, bus backpressure,
   model version, sample rate. Doubles as proof it's genuinely streaming.

---

## Configuration

Copy `backend/.env.example` → `backend/.env` (or set env vars). Highlights:

- `ENABLE_ETH=true` + `ETH_WS_URL=...` to add the Ethereum pending-tx feed (needs a
  free WS RPC key; relies on sampling — Part 10.3).
- `SAR_MODEL=groq/llama-3.1-70b-versatile` (+`GROQ_API_KEY`) for LLM-drafted SARs;
  unset = deterministic template SAR (graceful degradation).
- `REDIS_URL=...` to swap the in-process bus for Redis Streams (scale path).
- `DATABASE_URL=postgresql://...` for Supabase/Neon instead of local SQLite.

---

## Deploy ($0 path)

- **UI → Vercel:** import `ui/`, set `NEXT_PUBLIC_API_BASE` to your backend URL.
- **Backend → Render/Fly/HF Spaces:** `render.yaml` is included (Docker, free plan,
  health check). Set optional `REDIS_URL` / `DATABASE_URL` / `SAR_MODEL` env.
- **Redis → Upstash**, **Postgres → Supabase/Neon**, all free tiers.
- **Sanctions lists → GitHub Actions** nightly (`.github/workflows/nightly-lists.yml`).

See **DEPLOY.md** for the step-by-step checklist (accounts + env you provide).

---

## Robustness (Part 10), built in

- **Honest labels:** UI everywhere says "risk / suspected"; only sanctions exact-hits
  are called confirmed.
- **Connection resilience:** per-feed reconnect + exponential backoff + heartbeat;
  one feed dropping degrades gracefully (Health marks it down/stale).
- **Backpressure & sampling:** bounded queue, drop-oldest, adaptive sampling when
  the queue backs up.
- **Latency discipline:** LightGBM + set-lookup sanctions on the fast path; measured
  and displayed (p50/p95/p99). CI gate enforces the budget.
- **Feature parity:** the live feature builder and the trained model share one
  `FEATURE_NAMES` list; the parity CI gate fails the build on drift.
- **Graceful degradation:** feed down → demo source; model missing → heuristic;
  LLM unavailable → template SAR; Postgres unset → SQLite.

---

## Evaluation (Part 13)

```bash
PYTHONPATH=backend backend/.venv/bin/python -m aegis.eval.gates
```

Checks **feature-parity**, **fast-path latency p95** (single-digit ms budget), and
**model PR-AUC / recall** floors. Runs in CI on every push.

> The bundled model is trained on a **synthetic AMLSim-style** generator expressing
> the laundering typologies (fan-in/out, peeling, pass-through) in live-parity
> features, so PR-AUC is high by construction. Swap in the real **Elliptic** dataset
> via PyTorch Geometric (`train/train_model.py` already probes for it) for a
> labeled-history model; feature-parity is preserved by design.

---

## Architecture

```
ingestion (resilient WS)  →  event bus (backpressure/sampling)
   → rolling graph + live features
   → ensemble scoring [ sanctions screen | LightGBM | anomaly ]  → reason
   → alert engine (threshold/dedup/rate-limit) → subgraph explain → SAR draft
   → WebSocket hub → Surveillance Wall   (+ Postgres/SQLite store)
offline: synthetic-AMLSim/Elliptic → LightGBM + IsolationForest → pinned weights
```

Built solo, for $0. Live ingestion, an event bus with backpressure, a sliding-window
graph, a graph/ML ensemble, a GenAI SAR layer, and on-chain sanctions screening —
a rare combo, in one streaming system.
