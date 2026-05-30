"""Live structural anomaly (Part 5.3) — the hedge against novel laundering with
no list hit and no labeled precedent.

Isolation Forest over the live feature vector. If a trained model is present we
use it; otherwise a streaming robust z-score over recent features provides an
unsupervised anomaly signal with zero dependencies/training.
"""
from __future__ import annotations

import logging
import math
import os
from collections import deque

from ..conf.settings import settings
from ..stream.features import FEATURE_NAMES, feature_vector

log = logging.getLogger("aegis.anomaly")


class AnomalyScorer:
    def __init__(self) -> None:
        self.clf = None
        self.loaded = False
        # streaming stats for the fallback z-score path
        self._window: deque[list[float]] = deque(maxlen=2000)

    def load(self) -> None:
        path = settings.anomaly_path
        if not os.path.exists(path):
            log.info("No anomaly model at %s — streaming z-score fallback", path)
            return
        try:
            import joblib

            self.clf = joblib.load(path)
            self.loaded = True
            log.info("Loaded isolation-forest anomaly model")
        except Exception as e:  # noqa: BLE001
            log.warning("Anomaly load failed (%s) — z-score fallback", e)

    def score(self, feats: dict) -> float:
        vec = feature_vector(feats)
        if self.clf is not None:
            try:
                # score_samples: higher = more normal; invert + squash to 0..1.
                raw = float(self.clf.score_samples([vec])[0])
                return max(0.0, min(1.0, 1 / (1 + math.exp(raw + 0.5))))
            except Exception:  # noqa: BLE001
                pass
        return self._streaming_z(vec)

    def _streaming_z(self, vec: list[float]) -> float:
        self._window.append(vec)
        if len(self._window) < 30:
            return 0.1
        n = len(self._window)
        dims = len(vec)
        means = [0.0] * dims
        for row in self._window:
            for i in range(dims):
                means[i] += row[i]
        means = [m / n for m in means]
        vars_ = [1e-6] * dims
        for row in self._window:
            for i in range(dims):
                vars_[i] += (row[i] - means[i]) ** 2
        stds = [math.sqrt(v / n) + 1e-6 for v in vars_]
        zsq = sum(((vec[i] - means[i]) / stds[i]) ** 2 for i in range(dims))
        z = math.sqrt(zsq / dims)
        return max(0.0, min(1.0, z / 4.0))   # ~4 sigma -> 1.0


anomaly = AnomalyScorer()
