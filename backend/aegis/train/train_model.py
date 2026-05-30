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
def _licit_row() -> list[float]:
    value = random.expovariate(1 / 0.4)
    n_in = random.choice([1, 1, 1, 2])
    n_out = random.choice([1, 2, 2])
    return _row(value, n_in, n_out,
                src_in=random.randint(0, 2), src_out=random.randint(0, 3),
                dst_in=random.randint(0, 3), dst_out=random.randint(0, 2),
                max_out=random.randint(0, 3), max_in=random.randint(0, 3),
                fee=value * random.uniform(0.0005, 0.002),
                pass_through=random.random() < 0.05)


def _illicit_row() -> list[float]:
    typ = random.choice(["fanout", "fanin", "peeling", "passthrough"])
    if typ == "fanout":                       # distributor / smurfing
        n_in, n_out = 1, random.randint(8, 25)
        max_out = n_out
        max_in = random.randint(0, 2)
        pt = True
    elif typ == "fanin":                      # collector
        n_in, n_out = random.randint(8, 25), 1
        max_in = n_in
        max_out = random.randint(0, 2)
        pt = True
    elif typ == "peeling":                    # long peel chain
        n_in, n_out = 1, 2
        max_out = random.randint(4, 10)
        max_in = random.randint(2, 6)
        pt = True
    else:                                     # pass-through layering
        n_in, n_out = random.choice([1, 2]), random.choice([1, 2])
        max_out = random.randint(3, 8)
        max_in = random.randint(3, 8)
        pt = True
    value = random.uniform(0.5, 12)
    return _row(value, n_in, n_out,
                src_in=random.randint(1, 6), src_out=random.randint(1, 6),
                dst_in=random.randint(1, 6), dst_out=random.randint(1, 6),
                max_out=max_out, max_in=max_in,
                fee=value * random.uniform(0.0001, 0.001),
                pass_through=pt)


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
        "pass_through": 1.0 if pass_through else 0.0,
    }
    return [float(feats[n]) for n in FEATURE_NAMES]


def synth_dataset(n: int = 60000, illicit_frac: float = 0.02):
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
