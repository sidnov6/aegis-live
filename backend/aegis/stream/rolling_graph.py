"""Sliding-window in-memory transaction graph (Part 4.2).

Nodes = addresses, directed edges = transfers. Old transactions age out to bound
memory. This is what lets us compute live structural features the static Elliptic
dataset can't give us on the wire, and supplies the subgraph for alert explanation.
"""
from __future__ import annotations

import time
from collections import deque

import networkx as nx

from ..conf.settings import settings
from ..schema import Transaction


class RollingGraph:
    def __init__(self, window_seconds: int | None = None, max_nodes: int | None = None):
        self.window = window_seconds or settings.window_seconds
        self.max_nodes = max_nodes or settings.graph_max_nodes
        self.g = nx.DiGraph()
        # (ts, txid, [edges]) ordered for O(1) expiry from the left.
        self._events: deque[tuple[float, str, list[tuple[str, str]]]] = deque()

    def add(self, tx: Transaction) -> None:
        edges: list[tuple[str, str]] = []
        for src in tx.inputs or ["coinbase"]:
            for dst in tx.outputs or ["unspent"]:
                edges.append((src, dst))
        for src, dst in edges:
            if self.g.has_edge(src, dst):
                self.g[src][dst]["weight"] += 1
                self.g[src][dst]["value"] += tx.value
            else:
                self.g.add_edge(src, dst, weight=1, value=tx.value, txid=tx.txid)
            self.g.nodes[src].setdefault("first_seen", tx.ts)
            self.g.nodes[dst].setdefault("first_seen", tx.ts)
        self._events.append((tx.ts, tx.txid, edges))
        self._expire()

    def _expire(self) -> None:
        cutoff = time.time() - self.window
        while self._events and self._events[0][0] < cutoff:
            _, _, edges = self._events.popleft()
            for src, dst in edges:
                if self.g.has_edge(src, dst):
                    self.g[src][dst]["weight"] -= 1
                    if self.g[src][dst]["weight"] <= 0:
                        self.g.remove_edge(src, dst)
        # Hard cap on nodes (drop isolated/oldest) to bound memory.
        if self.g.number_of_nodes() > self.max_nodes:
            isolated = [n for n in self.g.nodes if self.g.degree(n) == 0]
            self.g.remove_nodes_from(isolated[: self.g.number_of_nodes() - self.max_nodes])

    # --- queries used by features + explanation -----------------------------
    def degree(self, addr: str) -> tuple[int, int]:
        if addr not in self.g:
            return (0, 0)
        return (self.g.in_degree(addr), self.g.out_degree(addr))

    def neighbors_subgraph(self, addr: str, radius: int = 1) -> dict:
        if addr not in self.g:
            return {"nodes": [{"id": addr}], "edges": []}
        und = self.g.to_undirected(as_view=True)
        nodes = set([addr])
        frontier = {addr}
        for _ in range(radius):
            nxt = set()
            for n in frontier:
                nxt |= set(und.neighbors(n))
            nodes |= nxt
            frontier = nxt
            if len(nodes) > 80:
                break
        sub = self.g.subgraph(nodes)
        return {
            "nodes": [{"id": n} for n in sub.nodes],
            "edges": [
                {"source": u, "target": v, "value": round(d.get("value", 0), 4)}
                for u, v, d in sub.edges(data=True)
            ],
        }

    def hops_to_set(self, addr: str, flagged: set[str], limit: int) -> int | None:
        """BFS distance (undirected) from addr to the nearest flagged address."""
        if addr in flagged:
            return 0
        if addr not in self.g:
            return None
        und = self.g.to_undirected(as_view=True)
        seen = {addr}
        frontier = {addr}
        for d in range(1, limit + 1):
            nxt: set[str] = set()
            for n in frontier:
                for m in und.neighbors(n):
                    if m in seen:
                        continue
                    if m in flagged:
                        return d
                    seen.add(m)
                    nxt.add(m)
            frontier = nxt
            if not frontier:
                break
        return None

    def stats(self) -> dict:
        return {
            "nodes": self.g.number_of_nodes(),
            "edges": self.g.number_of_edges(),
            "window_s": self.window,
        }
