"""FastAPI app: WebSocket push of the live stream + REST for alerts/health/SAR
actions. This is the serving layer behind the Surveillance Wall."""
from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from ..metrics import metrics
from ..pipeline import pipeline
from ..store import store
from .hub import hub

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await pipeline.start()
    yield
    await pipeline.shutdown()


app = FastAPI(title="AEGIS Live", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.get("/api/health")
async def health() -> dict:
    return pipeline.health()


@app.get("/api/metrics")
async def get_metrics() -> dict:
    return metrics.snapshot()


@app.get("/api/alerts")
async def get_alerts(limit: int = 100) -> dict:
    return {"alerts": store.recent_alerts(limit)}


@app.post("/api/alerts/{alert_id}/{action}")
async def act_on_alert(alert_id: str, action: str) -> dict:
    mapping = {"approve": "approved", "file": "filed", "dismiss": "dismissed"}
    status = mapping.get(action)
    if not status:
        return {"ok": False, "error": "unknown action"}
    store.update_status(alert_id, status)
    hub.broadcast({"type": "alert_status", "alert_id": alert_id, "status": status})
    return {"ok": True, "alert_id": alert_id, "status": status}


@app.post("/api/sar/{alert_id}")
async def generate_sar(alert_id: str) -> dict:
    """On-demand LLM SAR drafting (called when an analyst opens a case).

    Spending free-tier LLM tokens per human review — not per alert — keeps the
    deployment within free quotas and mirrors the real workflow. Falls back to
    the already-stored template SAR on any LLM error/quota limit."""
    from ..alerting.sar import draft_sar
    from ..schema import Alert

    rec = store.get_alert(alert_id)
    if not rec:
        return {"ok": False, "error": "alert not found"}
    alert = Alert(**rec)
    facts = {"subgraph": alert.subgraph, "features": {}}
    text, source = await asyncio.to_thread(draft_sar, alert, facts)
    store.set_sar(alert_id, text, source)
    hub.broadcast({"type": "sar_update", "alert_id": alert_id,
                   "sar_text": text, "sar_source": source})
    return {"ok": True, "alert_id": alert_id, "sar_text": text, "sar_source": source}


@app.get("/api/graph")
async def get_graph() -> dict:
    """Snapshot of the rolling graph for the live network view (bounded)."""
    g = pipeline.graph.g
    nodes = list(g.nodes)[:400]
    nodeset = set(nodes)
    edges = [
        {"source": u, "target": v, "value": round(d.get("value", 0), 4)}
        for u, v, d in g.edges(data=True)
        if u in nodeset and v in nodeset
    ][:800]
    return {"nodes": [{"id": n} for n in nodes], "edges": edges,
            "stats": pipeline.graph.stats()}


@app.websocket("/ws")
async def ws(websocket: WebSocket) -> None:
    await websocket.accept()
    q = hub.connect()
    try:
        # initial health snapshot so the UI paints immediately
        await websocket.send_text(json.dumps({"type": "health", **pipeline.health()}))
        while True:
            try:
                msg = await asyncio.wait_for(q.get(), timeout=5.0)
                await websocket.send_text(json.dumps(msg))
            except asyncio.TimeoutError:
                # periodic health heartbeat keeps the connection + UI fresh
                await websocket.send_text(
                    json.dumps({"type": "health", **pipeline.health()}))
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(q)
