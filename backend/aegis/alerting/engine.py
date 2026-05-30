"""Alert engine (Part 8): threshold + dedup (don't re-alert the same address every
block) + rate-limit (don't flood the analyst). Builds the explained, SAR-drafted
Alert object and persists it."""
from __future__ import annotations

import time
import uuid
from collections import deque

from ..conf.settings import settings
from ..schema import Alert, Transaction, Verdict
from ..stream.rolling_graph import RollingGraph
from .explain import build_explanation, primary_address
from .sar import template_sar


class AlertEngine:
    def __init__(self) -> None:
        self._recent: dict[str, float] = {}        # address -> last alert ts
        self._emitted: deque[float] = deque()      # ts of recent emissions (rate limit)
        self.total = 0

    def _rate_ok(self) -> bool:
        now = time.time()
        while self._emitted and self._emitted[0] < now - 60:
            self._emitted.popleft()
        return len(self._emitted) < settings.alert_rate_per_min

    def maybe_alert(
        self, tx: Transaction, verdict: Verdict, graph: RollingGraph
    ) -> Alert | None:
        if verdict.level not in ("high", "sanctioned"):
            return None

        addr = primary_address(tx, verdict)
        now = time.time()
        last = self._recent.get(addr, 0)
        if now - last < settings.alert_dedup_seconds:
            return None
        if not self._rate_ok():
            return None

        self._recent[addr] = now
        self._emitted.append(now)
        self.total += 1

        facts = build_explanation(tx, verdict, graph)
        alert = Alert(
            alert_id=str(uuid.uuid4())[:8],
            txid=tx.txid,
            chain=tx.chain,
            ts=verdict.ts,
            risk=verdict.risk,
            level=verdict.level,
            reason=verdict.reason,
            address=addr,
            subgraph=facts["subgraph"],
        )
        # Instant, free template SAR at creation; an LLM narrative is generated
        # on demand when an analyst opens the case (POST /api/sar/{id}).
        sar_text, source = template_sar(alert, facts)
        alert.sar_text = sar_text
        alert.sar_source = source
        return alert


alert_engine = AlertEngine()
