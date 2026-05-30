"""Tiny shared price cache used to enrich transactions with USD value."""
from __future__ import annotations

_PRICES: dict[str, float] = {"BTC": 0.0, "ETH": 0.0}


def set_price(chain: str, price: float) -> None:
    if price > 0:
        _PRICES[chain] = price


def get_price(chain: str) -> float:
    return _PRICES.get(chain, 0.0)


def to_usd(chain: str, native_value: float) -> float:
    return native_value * _PRICES.get(chain, 0.0)
