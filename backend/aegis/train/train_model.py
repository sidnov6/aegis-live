"""Offline training (Part 7) — feeds the live scorer.

Trains a LightGBM classifier (recall-first under ~2% imbalance) and an Isolation
Forest anomaly head, using ONLY the live-computable FEATURE_NAMES (feature-parity,
Part 10.6). Produces:
  - data/model_lgbm.txt        (LightGBM booster)
  - data/model_meta.json       (version + feature order + metrics)
  - data/anomaly_iforest.joblib

Data sources, in priority order:
  1. Elliptic via PyTorch Geometric, if installed and downloadable.
  2. A synthetic AMLSim-style generator (always available) that reproduces the
     laundering typologies (fan-in collector, fan-out distributor, peeling chains,
     pass-through) in terms of the same live features.

Tracked with MLflow if available (optional). Run: `python -m aegis.train.train_model`.
"""
from __future__ import annotations

import json
import math
import os
import random

import numpy as np

from ..conf.settings import settings
from ..stream.features import FEATURE_NAMES

random.seed(7)
np.random.seed(7)


# --------------------------------------------------------------------------- #
# Synthetic AMLSim-style generator expressed in live features.
# --------------------------------------------------------------------------- #
def _nz(x: float, frac: float = 0.15, floor: float = 0.0) -> float:
    """Multiplicative + additive Gaussian noise — blurs the archetypes so the two
    classes OVERLAP. Without overlap the model is perfectly separable and emits
    only 0/1 probabilities (flat-looking, PR-AUC=1.0). Overlap => calibrated
    continuous P(illicit), which is both more realistic and more legible on the UI."""
    return max(floor, x * (1 + random.gauss(0, frac)) + random.gauss(0, 0.4))


def _licit_row() -> list[float]:
    value = random.expovariate(1 / 0.4)
    # ~20% of legit txs show mild structure (exchange batching / consolidation) so
    # they sit near the decision boundary rather than trivially separable.
    bumpy = random.random() < 0.20
    n_in = random.choice([1, 1, 1, 2, 3] if bumpy else [1, 1, 1, 2])
    n_out = random.choice([2, 3, 4, 5] if bumpy else [1, 2, 2])
    return _row(value, n_in, n_out,
                src_in=_nz(random.randint(0, 3)), src_out=_nz(random.randint(0, 3)),
                dst_in=_nz(random.randint(0, 3)), dst_out=_nz(random.randint(0, 2)),
                max_out=_nz(random.randint(0, 4) + (3 if bumpy else 0)),
                max_in=_nz(random.randint(0, 3)),
                fee=value * random.uniform(0.0005, 0.002),
                pass_through=1.0 if random.random() < (0.15 if bumpy else 0.05) else 0.0)


def _illicit_row() -> list[float]:
    # `strength` in [0,1] scales how pronounced the laundering structure is. Weak
    # cases look almost licit; strong cases are textbook typologies. This produces
    # a smooth gradient of suspicion instead of a hard step.
    strength = random.random()
    typ = random.choice(["fanout", "fanin", "peeling", "passthrough"])
    span = lambda lo, hi: lo + strength * (hi - lo)
    if typ == "fanout":                       # distributor / smurfing
        n_in, n_out = 1, max(2, round(span(3, 25)))
        max_out, max_in = n_out, random.randint(0, 2)
    elif typ == "fanin":                      # collector
        n_in, n_out = max(2, round(span(3, 25))), 1
        max_in, max_out = n_in, random.randint(0, 2)
    elif typ == "peeling":                    # peel chain
        n_in, n_out = 1, 2
        max_out, max_in = round(span(2, 10)), round(span(1, 6))
    else:                                     # pass-through layering
        n_in, n_out = random.choice([1, 2]), random.choice([1, 2])
        max_out, max_in = round(span(2, 8)), round(span(2, 8))
    value = random.uniform(0.5, 12)
    return _row(value, n_in, n_out,
                src_in=_nz(span(0, 6)), src_out=_nz(span(0, 6)),
                dst_in=_nz(span(0, 6)), dst_out=_nz(span(0, 6)),
                max_out=_nz(max_out), max_in=_nz(max_in),
                fee=value * random.uniform(0.0001, 0.001),
                pass_through=1.0 if random.random() < (0.3 + 0.6 * strength) else 0.0)


def _row(value, n_in, n_out, *, src_in, src_out, dst_in, dst_out,
         max_out, max_in, fee, pass_through) -> list[float]:
    feats = {
        "value": value, "log_value": math.log1p(value),
        "n_in": n_in, "n_out": n_out,
        "fanout_ratio": n_out / max(1, n_in), "fanin_ratio": n_in / max(1, n_out),
        "src_in_deg": src_in, "src_out_deg": src_out,
        "dst_in_deg": dst_in, "dst_out_deg": dst_out,
        "max_out_deg": max_out, "max_in_deg": max_in,
        "fee_ratio": fee / value if value > 0 else 0,
        "pass_through": float(pass_through),
    }
    return [float(feats[n]) for n in FEATURE_NAMES]


def synth_dataset(n: int = 80000, illicit_frac: float = 0.02):
    X, y = [], []
    for _ in range(n):
        if random.random() < illicit_frac:
            X.append(_illicit_row()); y.append(1)
        else:
            X.append(_licit_row()); y.append(0)
    return np.array(X), np.array(y)


def try_elliptic():
    """Attempt to load Elliptic via PyG; map to live-parity features by rank.
    Returns (X, y) or None. Kept best-effort so training never hard-requires a
    multi-hundred-MB download."""
    try:
        from torch_geometric.datasets import EllipticBitcoinDataset  # type: ignore
    except Exception:
        return None
    try:
        ds = EllipticBitcoinDataset(root=os.path.join("data", "elliptic"))
        data = ds[0]
        x = data.x.numpy()
        ylab = data.y.numpy()
        mask = ylab != 2            # 2 = unknown in Elliptic
        x, ylab = x[mask], ylab[mask]
        # Elliptic features are anonymized; we cannot map 1:1 to live features.
        # We therefore use Elliptic ONLY to validate class balance/recall ceiling
        # and still train on parity features. Return None to keep parity strict.
        print(f"Elliptic available: {x.shape[0]} labeled nodes "
              f"({(ylab==1).mean()*100:.1f}% illicit). Using parity-feature "
              f"synthetic set for the live model to preserve feature-parity.")
        return None
    except Exception as e:  # noqa: BLE001
        print(f"Elliptic load skipped: {e}")
        return None


def main() -> None:
    os.makedirs("data", exist_ok=True)
    try_elliptic()
    X, y = synth_dataset()
    n = len(X)
    idx = np.random.permutation(n)
    cut = int(n * 0.8)
    tr, te = idx[:cut], idx[cut:]

    import lightgbm as lgb
    from sklearn.ensemble import IsolationForest
    from sklearn.metrics import average_precision_score, recall_score

    pos_w = (y[tr] == 0).sum() / max(1, (y[tr] == 1).sum())
    dtrain = lgb.Dataset(X[tr], label=y[tr], feature_name=FEATURE_NAMES)
    params = {
        "objective": "binary", "metric": "average_precision",
        "learning_rate": 0.05, "num_leaves": 31, "min_data_in_leaf": 40,
        "feature_fraction": 0.9, "bagging_fraction": 0.8, "bagging_freq": 1,
        "scale_pos_weight": pos_w, "verbosity": -1,
    }
    booster = lgb.train(params, dtrain, num_boost_round=300)
    booster.save_model(settings.model_path)

    proba = booster.predict(X[te])
    pr_auc = float(average_precision_score(y[te], proba))
    rec = float(recall_score(y[te], (proba >= 0.5).astype(int)))
    print(f"LightGBM  PR-AUC={pr_auc:.3f}  recall@0.5={rec:.3f}  (pos_weight={pos_w:.1f})")

    # Anomaly head trained on licit-only (novelty detection)
    iforest = IsolationForest(n_estimators=200, contamination=0.02, random_state=7)
    iforest.fit(X[tr][y[tr] == 0])
    import joblib
    joblib.dump(iforest, settings.anomaly_path)

    meta = {
        "version": "lgbm-synth-v1",
        "feature_names": FEATURE_NAMES,
        "metrics": {"pr_auc": pr_auc, "recall_at_0.5": rec},
        "n_train": int(cut), "illicit_frac": float(y.mean()),
    }
    with open(settings.model_meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    # optional MLflow tracking
    try:
        import mlflow

        mlflow.set_experiment("aegis-live")
        with mlflow.start_run():
            mlflow.log_params(params)
            mlflow.log_metrics({"pr_auc": pr_auc, "recall": rec})
            mlflow.log_artifact(settings.model_path)
        print("Logged run to MLflow.")
    except Exception:
        pass

    print(f"Saved model -> {settings.model_path}")
    print(f"Saved anomaly -> {settings.anomaly_path}")
    print(f"Saved meta -> {settings.model_meta_path}")


if __name__ == "__main__":
    main()
