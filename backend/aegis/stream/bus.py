"""Event bus that decouples ingestion from scoring so bursts don't block.

Default: an in-process bounded asyncio queue with drop-oldest backpressure and
optional reservoir-style sampling under load (Part 10.3). This is the $0 local
path. REDIS_URL switches to Redis Streams (Upstash) as the scale path — the
interface is identical so nothing downstream changes.
"""
from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field

from ..conf.settings import settings
from ..schema import Transaction


@dataclass
class BusMetrics:
    enqueued: int = 0
    dropped_backpressure: int = 0
    dropped_sampling: int = 0
    processed: int = 0
    depth: int = 0
    maxsize: int = 0

    def snapshot(self) -> dict:
        return {
            "enqueued": self.enqueued,
            "dropped_backpressure": self.dropped_backpressure,
            "dropped_sampling": self.dropped_sampling,
            "processed": self.processed,
            "depth": self.depth,
            "maxsize": self.maxsize,
        }


class EventBus:
    """Bounded async queue with drop-oldest backpressure + load sampling."""

    def __init__(self, maxsize: int | None = None, sample_rate: float | None = None):
        self.maxsize = maxsize or settings.bus_maxsize
        self.sample_rate = sample_rate if sample_rate is not None else settings.sample_rate
        self._q: asyncio.Queue[Transaction] = asyncio.Queue(maxsize=self.maxsize)
        self.metrics = BusMetrics(maxsize=self.maxsize)

    async def publish(self, tx: Transaction) -> None:
        # Sampling under load: keep a representative subset rather than choke.
        if self.sample_rate < 1.0 and random.random() > self.sample_rate:
            self.metrics.dropped_sampling += 1
            return
        try:
            self._q.put_nowait(tx)
        except asyncio.QueueFull:
            # Drop-oldest: make room for fresh data (recency matters most here).
            try:
                self._q.get_nowait()
                self.metrics.dropped_backpressure += 1
            except asyncio.QueueEmpty:
                pass
            try:
                self._q.put_nowait(tx)
            except asyncio.QueueFull:
                self.metrics.dropped_backpressure += 1
                return
        self.metrics.enqueued += 1
        self.metrics.depth = self._q.qsize()

    async def consume(self) -> Transaction:
        tx = await self._q.get()
        self.metrics.processed += 1
        self.metrics.depth = self._q.qsize()
        return tx

    def adapt_sampling(self) -> None:
        """Auto-throttle: tighten sampling when the queue is backing up."""
        fill = self._q.qsize() / max(1, self.maxsize)
        if fill > 0.85:
            self.sample_rate = max(0.1, self.sample_rate * 0.8)
        elif fill < 0.3 and self.sample_rate < 1.0:
            self.sample_rate = min(1.0, self.sample_rate * 1.1)
