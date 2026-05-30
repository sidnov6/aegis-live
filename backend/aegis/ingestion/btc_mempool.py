"""Bitcoin mempool firehose via blockchain.info (keyless, free, real-time).

Subscribe to unconfirmed transactions ("op":"unconfirmed_sub"). Each message is
a real BTC transaction we normalize into the canonical schema.
"""
from __future__ import annotations

import asyncio
import json
from typing import Awaitable, Callable

from ..conf.settings import settings
from ..schema import Transaction
from . import prices
from .resilience import FeedStatus, stream_with_resilience

_SUBSCRIBE = {"op": "unconfirmed_sub"}
_SATS = 1e8


def normalize_btc(raw: str) -> Transaction | None:
    try:
        msg = json.loads(raw)
        if msg.get("op") != "utx":
            return None
        x = msg["x"]
        txid = x["hash"]
        ins = x.get("inputs", [])
        outs = x.get("out", [])
        in_addrs = [
            i["prev_out"]["addr"]
            for i in ins
            if i.get("prev_out", {}).get("addr")
        ]
        out_addrs = [o["addr"] for o in outs if o.get("addr")]
        out_value_sats = sum(o.get("value", 0) for o in outs)
        in_value_sats = sum(
            i.get("prev_out", {}).get("value", 0) for i in ins
        )
        value_btc = out_value_sats / _SATS
        fee_btc = max(0.0, (in_value_sats - out_value_sats) / _SATS)
        return Transaction(
            txid=txid,
            chain="BTC",
            inputs=in_addrs,
            outputs=out_addrs,
            value=value_btc,
            value_usd=prices.to_usd("BTC", value_btc),
            fee=fee_btc,
            n_in=len(ins),
            n_out=len(outs),
            raw_hint="btc.mempool",
        )
    except (KeyError, ValueError, json.JSONDecodeError):
        return None


async def run_btc_mempool(
    on_tx: Callable[[Transaction], Awaitable[None]],
    status: FeedStatus,
    stop: asyncio.Event | None = None,
) -> None:
    async def on_raw(raw: str) -> None:
        tx = normalize_btc(raw)
        if tx is not None:
            await on_tx(tx)

    await stream_with_resilience(
        settings.btc_ws_url, _SUBSCRIBE, on_raw, status, stop=stop
    )
