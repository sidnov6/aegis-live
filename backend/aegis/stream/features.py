"""Live feature builder (Part 4.3).

CRITICAL DISCIPLINE (Part 7 feature-parity / Part 10.6): every feature here must
be computable from the live stream + rolling graph alone. The offline trainer
imports FEATURE_NAMES and the same `_feature_vector` shape so the model can never
depend on something the stream can't provide. This is the streaming analogue of
leakage prevention.
"""
from __future__ import annotations

import math

from ..schema import Transaction
from .rolling_graph import RollingGraph

# The single source of truth for feature order. Imported by train/ and scoring/.
FEATURE_NAMES = [
    "value",            # native value
    "log_value",
    "n_in",
    "n_out",
    "fanout_ratio",     # n_out / n_in
    "fanin_ratio",      # n_in / n_out
    "src_in_deg",       # primary input address in-degree (rolling)
    "src_out_deg",
    "dst_in_deg",       # primary output address in/out-degree
    "dst_out_deg",
    "max_out_deg",      # distributor signal
    "max_in_deg",       # collector signal
    "fee_ratio",
    "pass_through",     # 1 if an input address also recently received (in-then-out)
]


def build_features(tx: Transaction, graph: RollingGraph) -> dict:
    n_in = max(1, tx.n_in or len(tx.inputs) or 1)
    n_out = max(1, tx.n_out or len(tx.outputs) or 1)
    src = tx.inputs[0] if tx.inputs else "coinbase"
    dst = tx.outputs[0] if tx.outputs else "unspent"

    src_in, src_out = graph.degree(src)
    dst_in, dst_out = graph.degree(dst)

    out_degs = [graph.degree(a)[1] for a in (tx.outputs or [])] or [0]
    in_degs = [graph.degree(a)[0] for a in (tx.inputs or [])] or [0]

    # pass-through: an input address that recently *received* (in-then-out behavior)
    pass_through = 1.0 if any(graph.degree(a)[0] > 0 for a in (tx.inputs or [])) else 0.0

    feats = {
        "value": float(tx.value),
        "log_value": math.log1p(max(0.0, tx.value)),
        "n_in": float(n_in),
        "n_out": float(n_out),
        "fanout_ratio": n_out / n_in,
        "fanin_ratio": n_in / n_out,
        "src_in_deg": float(src_in),
        "src_out_deg": float(src_out),
        "dst_in_deg": float(dst_in),
        "dst_out_deg": float(dst_out),
        "max_out_deg": float(max(out_degs)),
        "max_in_deg": float(max(in_degs)),
        "fee_ratio": float(tx.fee / tx.value) if tx.value > 0 else 0.0,
        "pass_through": pass_through,
    }
    return feats


def feature_vector(feats: dict) -> list[float]:
    return [float(feats.get(name, 0.0)) for name in FEATURE_NAMES]
