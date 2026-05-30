"""Subgraph explanation (Part 8). For each alert, extract the triggering subgraph
from the rolling graph so the flag is defensible, not a bare score."""
from __future__ import annotations

from ..schema import Transaction, Verdict
from ..stream.rolling_graph import RollingGraph


def primary_address(tx: Transaction, verdict: Verdict) -> str:
    matched = verdict.components.get("sanctions", {}).get("matched")
    if matched:
        return matched
    if tx.inputs:
        return tx.inputs[0]
    if tx.outputs:
        return tx.outputs[0]
    return tx.txid


def build_explanation(tx: Transaction, verdict: Verdict, graph: RollingGraph) -> dict:
    addr = primary_address(tx, verdict)
    sub = graph.neighbors_subgraph(addr, radius=2)
    # annotate the flagged node + the tx endpoints for the UI
    flagged = verdict.components.get("sanctions", {}).get("matched")
    for node in sub["nodes"]:
        node["flagged"] = node["id"] == flagged
        node["subject"] = node["id"] == addr
        node["in_tx"] = node["id"] in tx.addresses()
    return {
        "subject": addr,
        "txid": tx.txid,
        "chain": tx.chain,
        "subgraph": sub,
        "features": verdict.components.get("features", {}),
    }
