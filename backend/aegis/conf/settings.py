"""Central configuration. Everything is env-overridable so the same code runs
locally ($0, keyless) and in the cloud with real keys.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


def _bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


@dataclass
class Settings:
    # ---- Ingestion ----------------------------------------------------------
    # BTC mempool firehose (keyless, free). blockchain.info is the simplest.
    btc_ws_url: str = os.getenv("BTC_WS_URL", "wss://ws.blockchain.info/inv")
    enable_btc: bool = _bool("ENABLE_BTC", True)

    # Binance public trade stream drives the price ticker (keyless, free).
    exchange_ws_url: str = os.getenv(
        "EXCHANGE_WS_URL",
        "wss://stream.binance.com:9443/stream?streams=btcusdt@trade/ethusdt@trade",
    )
    enable_exchange: bool = _bool("ENABLE_EXCHANGE", True)

    # Optional Ethereum pending-tx feed (needs a free WS RPC key). Off by default.
    eth_ws_url: Optional[str] = os.getenv("ETH_WS_URL") or None
    enable_eth: bool = _bool("ENABLE_ETH", False)

    # ---- Stream / backpressure ---------------------------------------------
    bus_maxsize: int = _int("BUS_MAXSIZE", 5000)        # bounded queue
    sample_rate: float = _float("SAMPLE_RATE", 1.0)     # 1.0 = keep all; <1 sample
    redis_url: Optional[str] = os.getenv("REDIS_URL") or None  # optional Upstash

    # ---- Rolling graph ------------------------------------------------------
    window_seconds: int = _int("WINDOW_SECONDS", 300)   # sliding window size
    graph_max_nodes: int = _int("GRAPH_MAX_NODES", 6000)
    sanctions_hop_limit: int = _int("SANCTIONS_HOP_LIMIT", 2)

    # ---- Scoring ------------------------------------------------------------
    model_path: str = os.getenv("MODEL_PATH", "data/model_lgbm.txt")
    model_meta_path: str = os.getenv("MODEL_META_PATH", "data/model_meta.json")
    anomaly_path: str = os.getenv("ANOMALY_PATH", "data/anomaly_iforest.joblib")
    enable_gnn: bool = _bool("ENABLE_GNN", False)       # heavy; off by default

    # ensemble weights (sanctions dominates via override, not weight)
    w_model: float = _float("W_MODEL", 0.55)
    w_anomaly: float = _float("W_ANOMALY", 0.45)
    alert_threshold: float = _float("ALERT_THRESHOLD", 0.72)

    # ---- Alerting ----------------------------------------------------------
    alert_dedup_seconds: int = _int("ALERT_DEDUP_SECONDS", 120)
    alert_rate_per_min: int = _int("ALERT_RATE_PER_MIN", 60)

    # ---- SAR / LLM ---------------------------------------------------------
    # LiteLLM model string, e.g. "groq/llama-3.1-70b", "gemini/gemini-1.5-flash",
    # "ollama/llama3". Empty => deterministic template SAR (graceful degradation).
    sar_model: Optional[str] = os.getenv("SAR_MODEL") or None

    # ---- Sanctions lists ---------------------------------------------------
    lists_dir: str = os.getenv("LISTS_DIR", "lists")

    # ---- Storage -----------------------------------------------------------
    # SQLite by default (zero-config); set DATABASE_URL for Postgres (Supabase/Neon).
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///data/aegis.db")

    # ---- Demo mode ---------------------------------------------------------
    # If live feeds are unreachable, synthesize a realistic stream so the demo
    # always has motion. Real feeds take priority when available.
    demo_fallback: bool = _bool("DEMO_FALLBACK", True)
    # Force-inject occasional sanctioned-address hits for the demo red-bloom.
    demo_inject_sanctions: bool = _bool("DEMO_INJECT_SANCTIONS", True)


settings = Settings()
