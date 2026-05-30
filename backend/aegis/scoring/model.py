"""Trained-model inference (Part 5.2) — the ML substance.

Loads a LightGBM model trained offline (train/train_model.py) on Elliptic/AMLSim
with live-parity features. Microsecond per-tx inference — the streaming workhorse.

Graceful degradation (Part 10.8): if no model file is present, fall back to a
transparent heuristic over the same features so the system still produces a
model_score and the demo runs before any training has happened.
"""
from __future__ import annotations

import json
import logging
import math
import os

from ..conf.settings import settings
from ..stream.features import FEATURE_NAMES, feature_vector

log = logging.getLogger("aegis.model")


class RiskModel:
    def __init__(self) -> None:
        self.booster = None
        self.version = "heuristic-fallback"
        self.feature_names = FEATURE_NAMES
        self.loaded = False

    def load(self) -> None:
        path = settings.model_path
        if not os.path.exists(path):
            log.warning("No model at %s — using heuristic fallback", path)
            return
        try:
            import lightgbm as lgb

            self.booster = lgb.Booster(model_file=path)
            if os.path.exists(settings.model_meta_path):
                with open(settings.model_meta_path) as f:
                    meta = json.load(f)
                self.version = meta.get("version", "lgbm")
                self.feature_names = meta.get("feature_names", FEATURE_NAMES)
            else:
                self.version = "lgbm"
            self.loaded = True
            log.info("Loaded model version=%s", self.version)
        except Exception as e:  # noqa: BLE001
            log.warning("Model load failed (%s) — heuristic fallback", e)
            self.booster = None

    def predict(self, feats: dict) -> float:
        if self.booster is not None:
            vec = [float(feats.get(n, 0.0)) for n in self.feature_names]
            try:
                p = float(self.booster.predict([vec])[0])
                return max(0.0, min(1.0, p))
            except Exception:  # noqa: BLE001
                pass
        return self._heuristic(feats)

    @staticmethod
    def _heuristic(feats: dict) -> float:
        """Transparent stand-in capturing well-known laundering shapes.
        Replaced by the trained model once train/ has run."""
        z = -2.2
        z += 0.9 * math.log1p(feats.get("max_out_deg", 0)) / 3      # distributor
        z += 0.8 * math.log1p(feats.get("max_in_deg", 0)) / 3       # collector
        z += 0.6 * feats.get("pass_through", 0)                     # in-then-out
        z += 0.5 * math.log1p(feats.get("fanout_ratio", 1)) / 2
        z += 0.4 * math.log1p(feats.get("value", 0)) / 4
        return 1 / (1 + math.exp(-z))


model = RiskModel()
