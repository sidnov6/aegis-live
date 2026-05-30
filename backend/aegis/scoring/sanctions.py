"""Sanctions / known-illicit address screening (Part 5.1) — the concrete,
explainable, true-positive-grade signal.

Loads flagged addresses (OFAC SDN digital-currency + community sets) into a fast
in-memory set, refreshed by lists/refresh.py. Screens each live tx for:
  - exact hit (the address IS flagged)        -> distance 0
  - sends-to / receives-from a flagged address -> distance 0/1
  - within N hops in the rolling graph         -> distance d
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

from ..conf.settings import settings
from ..schema import Transaction
from ..stream.rolling_graph import RollingGraph


@dataclass
class SanctionsResult:
    hit: bool
    distance: int | None         # 0 = direct, 1..N = hops away
    matched_address: str | None
    source: str | None           # which list
    reason: str


class SanctionsScreen:
    def __init__(self) -> None:
        self.flagged: set[str] = set()
        self.meta: dict[str, dict] = {}   # addr -> {source, entity}
        self.loaded_from: list[str] = []

    def load(self) -> int:
        """Load every *.json / *.txt list in the lists directory."""
        self.flagged.clear()
        self.meta.clear()
        self.loaded_from.clear()
        d = settings.lists_dir
        if not os.path.isdir(d):
            return 0
        for fn in sorted(os.listdir(d)):
            path = os.path.join(d, fn)
            try:
                if fn.endswith(".json"):
                    with open(path) as f:
                        data = json.load(f)
                    entries = data.get("addresses", data) if isinstance(data, dict) else data
                    for e in entries:
                        if isinstance(e, str):
                            addr, src, entity = e, fn, ""
                        else:
                            addr = e.get("address") or e.get("addr")
                            src = e.get("source", fn)
                            entity = e.get("entity", e.get("name", ""))
                        if addr:
                            self.flagged.add(addr)
                            self.meta[addr] = {"source": src, "entity": entity}
                    self.loaded_from.append(fn)
                elif fn.endswith(".txt"):
                    with open(path) as f:
                        for line in f:
                            addr = line.strip()
                            if addr and not addr.startswith("#"):
                                self.flagged.add(addr)
                                self.meta[addr] = {"source": fn, "entity": ""}
                    self.loaded_from.append(fn)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
        return len(self.flagged)

    def sample(self, n: int = 50) -> list[str]:
        out = []
        for a in self.flagged:
            out.append(a)
            if len(out) >= n:
                break
        return out

    def screen(self, tx: Transaction, graph: RollingGraph) -> SanctionsResult:
        if not self.flagged:
            return SanctionsResult(False, None, None, None, "")

        # 1) Exact / direct involvement.
        for addr in tx.addresses():
            if addr in self.flagged:
                m = self.meta.get(addr, {})
                entity = m.get("entity") or "known-illicit entity"
                side = "input" if addr in tx.inputs else "output"
                return SanctionsResult(
                    True, 0, addr, m.get("source"),
                    f"Direct match: {side} address is flagged ({entity})",
                )

        # 2) N-hop proximity in the rolling graph.
        best: tuple[int, str] | None = None
        for addr in tx.addresses():
            d = graph.hops_to_set(addr, self.flagged, settings.sanctions_hop_limit)
            if d is not None and (best is None or d < best[0]):
                best = (d, addr)
        if best is not None:
            d, addr = best
            return SanctionsResult(
                True, d, addr, "rolling-graph",
                f"{d} hop(s) from a known-illicit address in the live graph",
            )

        return SanctionsResult(False, None, None, None, "")


sanctions = SanctionsScreen()
