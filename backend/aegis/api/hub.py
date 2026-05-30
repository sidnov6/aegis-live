"""Fan-out hub: broadcasts pipeline events to all connected WebSocket clients.
Each client gets its own bounded queue (slow clients drop frames, never block
the pipeline)."""
from __future__ import annotations

import asyncio
import json
from collections import deque


class Hub:
    def __init__(self) -> None:
        self._clients: set[asyncio.Queue] = set()
        # small ring buffer so a freshly-connected UI gets immediate motion
        self._recent: deque[dict] = deque(maxlen=120)

    def connect(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        for msg in self._recent:
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                break
        self._clients.add(q)
        return q

    def disconnect(self, q: asyncio.Queue) -> None:
        self._clients.discard(q)

    def broadcast(self, msg: dict) -> None:
        if msg.get("type") in ("tx", "alert"):
            self._recent.append(msg)
        dead = []
        for q in self._clients:
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                try:
                    q.get_nowait()        # drop oldest for slow client
                    q.put_nowait(msg)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    dead.append(q)
        for q in dead:
            self._clients.discard(q)

    @property
    def client_count(self) -> int:
        return len(self._clients)


hub = Hub()
