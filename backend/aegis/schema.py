"""Canonical event schemas shared across the pipeline.

The whole system speaks one language: a normalized `Transaction`. Every source
adapter must produce these; every downstream stage consumes them.
"""
from __future__ import annotations

import time
from typing import Literal, Optional

from pydantic import BaseModel, Field

Chain = Literal["BTC", "ETH"]


class Transaction(BaseModel):
    """A normalized, source-agnostic transfer event."""

    txid: str
    chain: Chain
    ts: float = Field(default_factory=time.time)        # unix seconds (ingest time)
    inputs: list[str] = Field(default_factory=list)     # source addresses
    outputs: list[str] = Field(default_factory=list)    # destination addresses
    value: float = 0.0                                  # native units (BTC/ETH)
    value_usd: float = 0.0                              # enriched from ticker
    fee: float = 0.0
    n_in: int = 0
    n_out: int = 0
    raw_hint: str = ""                                  # short provenance note

    def addresses(self) -> list[str]:
        return list(dict.fromkeys([*self.inputs, *self.outputs]))


class Verdict(BaseModel):
    """Output of the scoring ensemble for one transaction."""

    txid: str
    chain: Chain
    ts: float
    risk: float                                         # 0..1 ensemble risk
    level: Literal["cleared", "elevated", "high", "sanctioned"]
    reason: str                                         # human-readable
    sanctions_hit: bool = False
    sanctions_distance: Optional[int] = None            # hops to nearest flagged
    model_score: float = 0.0
    anomaly_score: float = 0.0
    value_usd: float = 0.0
    latency_ms: float = 0.0
    components: dict = Field(default_factory=dict)      # detail for the UI


class Ticker(BaseModel):
    """A live price tick for the moving ticker."""

    symbol: str
    price: float
    ts: float = Field(default_factory=time.time)
    qty: float = 0.0


class Alert(BaseModel):
    """A raised alert with explanation and (optional) drafted SAR."""

    alert_id: str
    txid: str
    chain: Chain
    ts: float
    risk: float
    level: str
    reason: str
    address: str                                        # primary subject address
    subgraph: dict = Field(default_factory=dict)        # nodes/edges for the UI
    sar_text: Optional[str] = None
    sar_source: Optional[str] = None                    # "llm:<model>" | "template"
    status: Literal["open", "approved", "filed", "dismissed"] = "open"
