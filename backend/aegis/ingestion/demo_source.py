"""Synthetic stream — graceful degradation when live feeds are unreachable
(offline dev, locked-down networks). Produces realistic-looking BTC transactions
with occasional laundering typologies (fan-out, peeling chains) and, optionally,
hits against the loaded sanctions list so the red-bloom demo always works.

Real feeds always take priority; this only runs as a fallback or alongside.
"""
from __future__ import annotations

import asyncio
import random
import string
import time
from typing import Awaitable, Callable

from ..schema import Transaction
from . import prices
from .resilience import FeedStatus


def _addr(prefix: str = "1") -> str:
    return prefix + "".join(
        random.choices(string.ascii_letters + string.digits, k=33)
    )


class DemoSource:
    def __init__(self, sanctioned_pool: list[str] | None = None) -> None:
        # A small recurring address universe so the rolling graph forms structure.
        self.universe = [_addr() for _ in range(400)]
        self.sanctioned_pool = sanctioned_pool or []

    def _normal_tx(self) -> Transaction:
        n_in = random.choices([1, 1, 1, 2, 3], k=1)[0]
        n_out = random.choices([1, 2, 2, 3], k=1)[0]
        ins = random.sample(self.universe, n_in)
        outs = random.sample(self.universe, n_out)
        value = round(random.expovariate(1 / 0.35), 6)
        return Transaction(
            txid="demo-" + _addr("")[:16],
            chain="BTC",
            inputs=ins,
            outputs=outs,
            value=value,
            value_usd=prices.to_usd("BTC", value) or value * 60000,
            fee=round(value * 0.001, 8),
            n_in=n_in,
            n_out=n_out,
            raw_hint="demo.normal",
        )

    def _fanout_tx(self) -> Transaction:
        """Distributor pattern: 1 in -> many out (smurfing-like)."""
        ins = random.sample(self.universe, 1)
        outs = [_addr() for _ in range(random.randint(8, 20))]
        value = round(random.uniform(2, 8), 4)
        return Transaction(
            txid="demo-" + _addr("")[:16],
            chain="BTC",
            inputs=ins,
            outputs=outs,
            value=value,
            value_usd=prices.to_usd("BTC", value) or value * 60000,
            n_in=1,
            n_out=len(outs),
            raw_hint="demo.fanout",
        )

    def _sanctioned_tx(self) -> Transaction:
        """A transaction touching a known-illicit address (true-positive grade)."""
        flagged = random.choice(self.sanctioned_pool)
        if random.random() < 0.5:
            ins, outs = [flagged], random.sample(self.universe, 2)
        else:
            ins, outs = random.sample(self.universe, 1), [flagged, random.choice(self.universe)]
        value = round(random.uniform(0.5, 5), 4)
        return Transaction(
            txid="demo-" + _addr("")[:16],
            chain="BTC",
            inputs=ins,
            outputs=outs,
            value=value,
            value_usd=prices.to_usd("BTC", value) or value * 60000,
            n_in=len(ins),
            n_out=len(outs),
            raw_hint="demo.sanctioned",
        )

    def next_tx(self, inject_sanctions: bool) -> Transaction:
        r = random.random()
        if inject_sanctions and self.sanctioned_pool and r < 0.02:
            return self._sanctioned_tx()
        if r < 0.08:
            return self._fanout_tx()
        return self._normal_tx()


async def run_demo_source(
    on_tx: Callable[[Transaction], Awaitable[None]],
    status: FeedStatus,
    sanctioned_pool: list[str],
    inject_sanctions: bool,
    rate_per_sec: float = 4.0,
    stop: asyncio.Event | None = None,
) -> None:
    src = DemoSource(sanctioned_pool)
    status.connected = True
    if not prices.get_price("BTC"):
        prices.set_price("BTC", 60000.0)
    while not (stop and stop.is_set()):
        tx = src.next_tx(inject_sanctions)
        status.last_event_ts = time.time()
        status.events += 1
        await on_tx(tx)
        await asyncio.sleep(max(0.01, random.expovariate(rate_per_sec)))
    status.connected = False
