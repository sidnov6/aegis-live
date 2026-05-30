"""Eval + CI gates (Part 13). Run in CI to block regressions:
  - feature-parity: live feature builder matches the trained model's feature set
  - latency: fast-path scoring stays in the single-digit-ms budget
  - detection: model PR-AUC / recall above floors (from model_meta.json)
Exit non-zero on failure. Run: `python -m aegis.eval.gates`.
"""
from __future__ import annotations

import json
import os
import sys
import time

from ..conf.settings import settings
from ..scoring.anomaly import anomaly
from ..scoring.ensemble import score_transaction
from ..scoring.model import model
from ..scoring.sanctions import sanctions
from ..schema import Transaction
from ..stream.features import FEATURE_NAMES
from ..stream.rolling_graph import RollingGraph

PR_AUC_FLOOR = 0.60
RECALL_FLOOR = 0.60
LATENCY_P95_MS = 8.0


def gate_parity() -> bool:
    if not os.path.exists(settings.model_meta_path):
        print("PARITY: no model_meta.json (model not trained) — skipped (warn)")
        return True
    with open(settings.model_meta_path) as f:
        meta = json.load(f)
    trained = meta.get("feature_names", [])
    ok = trained == FEATURE_NAMES
    print(f"PARITY: {'OK' if ok else 'MISMATCH'} "
          f"(trained={len(trained)}, live={len(FEATURE_NAMES)})")
    if not ok:
        print(f"  trained: {trained}\n  live:    {FEATURE_NAMES}")
    return ok


def gate_latency() -> bool:
    sanctions.load(); model.load(); anomaly.load()
    g = RollingGraph()
    lat = []
    for i in range(2000):
        tx = Transaction(txid=f"t{i}", chain="BTC",
                         inputs=[f"a{i%50}"], outputs=[f"b{i%70}", f"c{i%30}"],
                         value=0.5, n_in=1, n_out=2)
        g.add(tx)
        t0 = time.perf_counter()
        score_transaction(tx, g)
        lat.append((time.perf_counter() - t0) * 1000)
    lat.sort()
    p95 = lat[int(0.95 * len(lat))]
    ok = p95 <= LATENCY_P95_MS
    print(f"LATENCY: p95={p95:.3f}ms (budget {LATENCY_P95_MS}ms) {'OK' if ok else 'FAIL'}")
    return ok


def gate_detection() -> bool:
    if not os.path.exists(settings.model_meta_path):
        print("DETECTION: no model_meta.json — skipped (warn)")
        return True
    with open(settings.model_meta_path) as f:
        m = json.load(f).get("metrics", {})
    pr, rec = m.get("pr_auc", 0), m.get("recall_at_0.5", 0)
    ok = pr >= PR_AUC_FLOOR and rec >= RECALL_FLOOR
    print(f"DETECTION: PR-AUC={pr:.3f}(>= {PR_AUC_FLOOR}) "
          f"recall={rec:.3f}(>= {RECALL_FLOOR}) {'OK' if ok else 'FAIL'}")
    return ok


def main() -> int:
    results = [gate_parity(), gate_latency(), gate_detection()]
    if all(results):
        print("\nALL GATES PASSED")
        return 0
    print("\nGATE FAILURE")
    return 1


if __name__ == "__main__":
    sys.exit(main())
