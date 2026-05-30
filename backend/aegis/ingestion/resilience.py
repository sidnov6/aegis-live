"""Connection resilience: auto-reconnect, exponential backoff, heartbeat,
resubscribe-on-reconnect. One resilient client per source so a single feed
dropping never takes the system down (Part 10.2).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Optional

import websockets
from websockets.exceptions import ConnectionClosed

log = logging.getLogger("aegis.ingest")


class FeedStatus:
    """Shared, observable status for one feed (powers the Health screen)."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.connected = False
        self.last_event_ts: float = 0.0
        self.events = 0
        self.reconnects = 0
        self.last_error: str = ""

    def snapshot(self) -> dict:
        import time

        stale = (time.time() - self.last_event_ts) > 15 if self.last_event_ts else True
        return {
            "name": self.name,
            "connected": self.connected,
            "stale": bool(self.connected and stale),
            "events": self.events,
            "reconnects": self.reconnects,
            "last_event_age_s": round(time.time() - self.last_event_ts, 1)
            if self.last_event_ts
            else None,
            "last_error": self.last_error,
        }


async def stream_with_resilience(
    url: str,
    subscribe_msg: Optional[dict],
    on_raw: Callable[[str], Awaitable[None]],
    status: FeedStatus,
    *,
    ping_interval: int = 20,
    max_backoff: int = 30,
    stop: Optional[asyncio.Event] = None,
) -> None:
    """Hold a resilient WebSocket connection forever (until `stop` is set)."""
    import json
    import time

    backoff = 1
    while not (stop and stop.is_set()):
        try:
            async with websockets.connect(
                url, ping_interval=ping_interval, ping_timeout=ping_interval, max_queue=2048
            ) as ws:
                if subscribe_msg is not None:
                    await ws.send(json.dumps(subscribe_msg))
                status.connected = True
                backoff = 1  # reset on a successful connection
                log.info("[%s] connected", status.name)
                async for raw in ws:
                    status.last_event_ts = time.time()
                    status.events += 1
                    await on_raw(raw)
                    if stop and stop.is_set():
                        break
        except asyncio.CancelledError:
            raise
        except (ConnectionClosed, OSError, Exception) as e:  # noqa: BLE001
            status.connected = False
            status.reconnects += 1
            status.last_error = f"{type(e).__name__}: {e}"
            log.warning("[%s] disconnected (%s); backoff %ss", status.name, e, backoff)
            await asyncio.sleep(min(backoff, max_backoff))
            backoff *= 2
    status.connected = False
