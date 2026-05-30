"""Exchange trade stream -> live price ticker + USD enrichment.

Free, keyless, real-time. Drives the moving number on the wall and feeds
prices.to_usd() so transactions get a USD size.

Resilience (Part 10.2/10.8): Binance is the primary provider, but it returns
HTTP 451 from some datacenter regions (e.g. cloud hosts). So we keep an ordered
list of providers and auto-rotate to Coinbase (not geo-blocked) after repeated
failures — the ticker stays alive wherever the backend runs.
"""
from __future__ import annotations

import asyncio
import json
from typing import Awaitable, Callable

import websockets
from websockets.exceptions import ConnectionClosed

from ..conf.settings import settings
from ..schema import Ticker
from . import prices
from .resilience import FeedStatus


def _norm_binance(raw: str) -> Ticker | None:
    try:
        msg = json.loads(raw)
        data = msg.get("data", msg)
        if data.get("e") != "trade":
            return None
        symbol = data["s"]                     # e.g. BTCUSDT
        price = float(data["p"])
        chain = {"BTCUSDT": "BTC", "ETHUSDT": "ETH"}.get(symbol)
        if chain:
            prices.set_price(chain, price)
        return Ticker(symbol=symbol, price=price, qty=float(data.get("q", 0)))
    except (KeyError, ValueError, json.JSONDecodeError):
        return None


def _norm_coinbase(raw: str) -> Ticker | None:
    try:
        data = json.loads(raw)
        if data.get("type") != "ticker" or "price" not in data:
            return None
        pid = data["product_id"]               # e.g. BTC-USD
        price = float(data["price"])
        sym = pid.replace("-USD", "USDT")      # normalize to the UI's symbol
        chain = {"BTC-USD": "BTC", "ETH-USD": "ETH"}.get(pid)
        if chain:
            prices.set_price(chain, price)
        return Ticker(symbol=sym, price=price, qty=float(data.get("last_size", 0)))
    except (KeyError, ValueError, json.JSONDecodeError):
        return None


# Primary first; rotate on repeated failure.
def _providers() -> list[dict]:
    return [
        {"name": "binance", "url": settings.exchange_ws_url,
         "subscribe": None, "normalize": _norm_binance},
        {"name": "coinbase", "url": "wss://ws-feed.exchange.coinbase.com",
         "subscribe": {"type": "subscribe", "product_ids": ["BTC-USD", "ETH-USD"],
                       "channels": ["ticker"]},
         "normalize": _norm_coinbase},
    ]


async def run_exchange_ticker(
    on_ticker: Callable[[Ticker], Awaitable[None]],
    status: FeedStatus,
    stop: asyncio.Event | None = None,
) -> None:
    import time

    providers = _providers()
    idx = 0
    consecutive_fail = 0
    backoff = 1
    while not (stop and stop.is_set()):
        p = providers[idx]
        try:
            async with websockets.connect(p["url"], ping_interval=20) as ws:
                if p["subscribe"] is not None:
                    await ws.send(json.dumps(p["subscribe"]))
                status.connected = True
                status.name = f"exchange:{p['name']}"
                consecutive_fail = 0
                backoff = 1
                async for raw in ws:
                    tick = p["normalize"](raw)
                    if tick is not None:
                        status.last_event_ts = time.time()
                        status.events += 1
                        await on_ticker(tick)
                    if stop and stop.is_set():
                        break
        except asyncio.CancelledError:
            raise
        except (ConnectionClosed, OSError, Exception) as e:  # noqa: BLE001
            status.connected = False
            status.reconnects += 1
            status.last_error = f"{p['name']}: {type(e).__name__}: {e}"
            consecutive_fail += 1
            if consecutive_fail >= 3 and len(providers) > 1:
                idx = (idx + 1) % len(providers)        # rotate provider
                consecutive_fail = 0
                backoff = 1
            await asyncio.sleep(min(backoff, 30))
            backoff *= 2
    status.connected = False
