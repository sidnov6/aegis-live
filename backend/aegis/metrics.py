"""Prometheus-style live counters + latency distribution (Part 10.7, Part 13)."""
from __future__ import annotations

import time
from collections import deque


class Metrics:
    def __init__(self) -> None:
        self.start = time.time()
        self.scored = 0
        self.flagged = 0
        self.sanctioned_hits = 0
        self.alerts = 0
        self._latencies: deque[float] = deque(maxlen=2000)
        self._score_ts: deque[float] = deque(maxlen=5000)

    def record_score(self, latency_ms: float, level: str) -> None:
        self.scored += 1
        self._latencies.append(latency_ms)
        self._score_ts.append(time.time())
        if level in ("high", "sanctioned"):
            self.flagged += 1
        if level == "sanctioned":
            self.sanctioned_hits += 1

    def tx_per_sec(self) -> float:
        now = time.time()
        recent = [t for t in self._score_ts if t > now - 5]
        return round(len(recent) / 5.0, 2)

    def _pct(self, p: float) -> float:
        if not self._latencies:
            return 0.0
        s = sorted(self._latencies)
        idx = min(len(s) - 1, int(p * len(s)))
        return round(s[idx], 3)

    def snapshot(self) -> dict:
        return {
            "uptime_s": round(time.time() - self.start, 1),
            "scored": self.scored,
            "flagged": self.flagged,
            "sanctioned_hits": self.sanctioned_hits,
            "alerts": self.alerts,
            "tx_per_sec": self.tx_per_sec(),
            "latency_ms_p50": self._pct(0.50),
            "latency_ms_p95": self._pct(0.95),
            "latency_ms_p99": self._pct(0.99),
        }


metrics = Metrics()
