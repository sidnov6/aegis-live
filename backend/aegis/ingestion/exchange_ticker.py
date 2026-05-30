"""Binance public trade stream -> live price ticker + USD enrichment.

Free, keyless, real-time. Drives the moving number on the wall and feeds
prices.to_usd() so transactions get a USD size.
"""
from __future__ import annotations

import asyncio
import json
from typing import Awaitable, Callable

from ..conf.settings import settings
from ..schema import Ticker
from . import prices
from .resilience import FeedStatus, stream_with_resilience

_SYMBOL_TO_CHAIN = {"BTCUSDT": "BTC", "ETHUSDT": "ETH"}


def normalize_trade(raw: str) -> Ticker | None:
    try:
        msg = json.loads(raw)
        data = msg.get("data", msg)
        if data.get("e") != "trade":
            return None
        symbol = data["s"]
        price = float(data["p"])
        qty = float(data["q"])
        chain = _SYMBOL_TO_CHAIN.get(symbol)
        if chain:
            prices.set_price(chain, price)
        return Ticker(symbol=symbol, price=price, qty=qty)
    except (KeyError, ValueError, json.JSONDecodeError):
        return None


async def run_exchange_ticker(
    on_ticker: Callable[[Ticker], Awaitable[None]],
    status: FeedStatus,
    stop: asyncio.Event | None = None,
) -> None:
    async def on_raw(raw: str) -> None:
        tick = normalize_trade(raw)
        if tick is not None:
            await on_ticker(tick)

    # Binance combined-stream endpoint needs no subscribe message (streams in URL).
    await stream_with_resilience(
        settings.exchange_ws_url, None, on_raw, status, stop=stop
    )
