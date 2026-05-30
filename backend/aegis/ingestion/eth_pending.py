"""Optional Ethereum pending-tx feed via eth_subscribe (WebSocket RPC only).

Off by default (needs a free WS RPC key in ETH_WS_URL). Pending-tx volume can be
thousands/sec, so this relies on the bus-level sampling/backpressure (Part 10.3).
We fetch tx bodies lazily only for a sampled subset to stay within free limits;
here we emit a lightweight Transaction from the hash + a best-effort body.
"""
from __future__ import annotations

import asyncio
import json
from typing import Awaitable, Callable

import websockets

from ..conf.settings import settings
from ..schema import Transaction
from . import prices
from .resilience import FeedStatus

_SUBSCRIBE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "eth_subscribe",
    "params": ["newPendingTransactions"],
}
_WEI = 1e18


async def run_eth_pending(
    on_tx: Callable[[Transaction], Awaitable[None]],
    status: FeedStatus,
    stop: asyncio.Event | None = None,
) -> None:
    if not settings.eth_ws_url:
        return
    import time

    backoff = 1
    while not (stop and stop.is_set()):
        try:
            async with websockets.connect(settings.eth_ws_url, ping_interval=20) as ws:
                await ws.send(json.dumps(_SUBSCRIBE))
                status.connected = True
                backoff = 1
                async for raw in ws:
                    status.last_event_ts = time.time()
                    status.events += 1
                    try:
                        msg = json.loads(raw)
                        params = msg.get("params", {})
                        txhash = params.get("result")
                        if not isinstance(txhash, str):
                            continue
                        # Lightweight event; body enrichment is sampled elsewhere.
                        tx = Transaction(
                            txid=txhash,
                            chain="ETH",
                            inputs=[],
                            outputs=[],
                            value=0.0,
                            value_usd=0.0,
                            raw_hint="eth.pending",
                        )
                        await on_tx(tx)
                    except (KeyError, ValueError, json.JSONDecodeError):
                        continue
                    if stop and stop.is_set():
                        break
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            status.connected = False
            status.reconnects += 1
            status.last_error = f"{type(e).__name__}: {e}"
            await asyncio.sleep(min(backoff, 30))
            backoff *= 2
    status.connected = False
