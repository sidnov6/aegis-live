"""Ensemble + reason (Part 5.4).

A sanctions hit dominates (it's ground-truth illicit by designation); otherwise
model + anomaly stack. Every verdict carries a human-readable reason — the flag
must be defensible, never a bare number.
"""
from __future__ import annotations

import time

from ..conf.settings import settings
from ..schema import Transaction, Verdict
from ..stream.features import build_features
from ..stream.rolling_graph import RollingGraph
from .anomaly import anomaly
from .model import model
from .sanctions import sanctions


def _level(risk: float, sanctioned: bool) -> str:
    if sanctioned:
        return "sanctioned"
    if risk >= settings.alert_threshold:
        return "high"
    if risk >= 0.45:
        return "elevated"
    return "cleared"


def score_transaction(tx: Transaction, graph: RollingGraph) -> Verdict:
    t0 = time.perf_counter()

    feats = build_features(tx, graph)
    sres = sanctions.screen(tx, graph)
    model_score = model.predict(feats)
    anom_score = anomaly.score(feats)

    if sres.hit:
        # Sanctioned: risk pinned high, decaying slightly with distance, but never
        # below the alert threshold for a confirmed proximity.
        risk = max(0.9, 1.0 - 0.05 * (sres.distance or 0))
        reason = sres.reason
        sanctioned = True
    else:
        risk = settings.w_model * model_score + settings.w_anomaly * anom_score
        risk = max(0.0, min(1.0, risk))
        sanctioned = False
        bits = []
        if model_score >= 0.6:
            bits.append(f"model P(illicit)={model_score:.2f}")
        if anom_score >= 0.6:
            bits.append(f"structural anomaly={anom_score:.2f}")
        if feats.get("max_out_deg", 0) >= 8:
            bits.append("distributor fan-out pattern")
        if feats.get("max_in_deg", 0) >= 8:
            bits.append("collector fan-in pattern")
        if feats.get("pass_through", 0):
            bits.append("pass-through (in-then-out)")
        reason = "; ".join(bits) if bits else "no notable risk signals"

    level = _level(risk, sanctioned)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    return Verdict(
        txid=tx.txid,
        chain=tx.chain,
        ts=tx.ts,
        risk=round(risk, 4),
        level=level,
        reason=reason,
        sanctions_hit=sres.hit,
        sanctions_distance=sres.distance,
        model_score=round(model_score, 4),
        anomaly_score=round(anom_score, 4),
        value_usd=round(tx.value_usd, 2),
        latency_ms=round(latency_ms, 3),
        components={
            "sanctions": {
                "hit": sres.hit,
                "distance": sres.distance,
                "matched": sres.matched_address,
                "source": sres.source,
            },
            "model": {"score": round(model_score, 4), "version": model.version},
            "anomaly": {"score": round(anom_score, 4)},
            "features": {k: round(v, 4) for k, v in feats.items()},
        },
    )
