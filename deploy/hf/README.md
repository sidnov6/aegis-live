---
title: AEGIS Live Backend
emoji: 🛡️
colorFrom: blue
colorTo: red
sdk: docker
app_port: 7860
pinned: false
short_description: Real-time streaming AML detection API (WebSocket + REST)
---

# AEGIS Live — Backend (STROMWACHE)

Real-time streaming AML detection on live blockchain transactions. This Space runs
the FastAPI backend: resilient WebSocket ingestion (BTC mempool + Binance ticker),
an event bus with backpressure, a sliding-window transaction graph, an ensemble
scorer (OFAC sanctions screen + LightGBM + structural anomaly), subgraph-explained
alerts, and LLM/template-drafted SARs.

- Health:  `/api/health`
- Live stream (WebSocket):  `/ws`
- Alerts:  `/api/alerts`

The UI (the Surveillance Wall) is deployed separately and points here via
`NEXT_PUBLIC_API_BASE`. Source: https://github.com/sidnov6/aegis-live

> Live risk scores are PREDICTIONS pending human review. Only sanctions exact-hits
> are ground-truth designations.
