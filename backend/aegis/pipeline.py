"""The pipeline orchestrator — wires every stage together (Part 2 flow):

  ingestion -> bus -> rolling graph + features -> ensemble scoring
            -> alert engine -> hub broadcast + store

Runs as a set of asyncio tasks managed by the FastAPI lifespan. Resilient and
degrades gracefully: if no live feed is reachable, the demo source supplies motion.
"""
from __future__ import annotations

import asyncio
import logging

from .alerting.engine import alert_engine
from .conf.settings import settings
from .ingestion.btc_mempool import run_btc_mempool
from .ingestion.demo_source import run_demo_source
from .ingestion.eth_pending import run_eth_pending
from .ingestion.exchange_ticker import run_exchange_ticker
from .ingestion.resilience import FeedStatus
from .metrics import metrics
from .scoring.anomaly import anomaly
from .scoring.ensemble import score_transaction
from .scoring.model import model
from .scoring.sanctions import sanctions
from .schema import Ticker, Transaction
from .store import store
from .stream.bus import EventBus
from .stream.rolling_graph import RollingGraph

log = logging.getLogger("aegis.pipeline")


class Pipeline:
    def __init__(self) -> None:
        from .api.hub import hub

        self.hub = hub
        self.bus = EventBus()
        self.graph = RollingGraph()
        self.stop = asyncio.Event()
        self.tasks: list[asyncio.Task] = []
        self.feeds: dict[str, FeedStatus] = {}
        self._live_seen = False

    # --- startup ------------------------------------------------------------
    def startup(self) -> None:
        n = sanctions.load()
        log.info("Sanctions list loaded: %d addresses from %s", n, sanctions.loaded_from)
        model.load()
        anomaly.load()

    async def start(self) -> None:
        self.startup()
        loop = asyncio.get_event_loop()

        async def on_tx(tx: Transaction) -> None:
            self._live_seen = True
            await self.bus.publish(tx)

        async def on_ticker(t: Ticker) -> None:
            self.hub.broadcast({"type": "ticker", "symbol": t.symbol,
                                "price": t.price, "ts": t.ts})

        # Ingestion tasks (each independently resilient)
        if settings.enable_exchange:
            st = FeedStatus("exchange:binance")
            self.feeds["exchange"] = st
            self.tasks.append(asyncio.create_task(
                run_exchange_ticker(on_ticker, st, self.stop)))
        if settings.enable_btc:
            st = FeedStatus("btc:mempool")
            self.feeds["btc"] = st
            self.tasks.append(asyncio.create_task(
                run_btc_mempool(on_tx, st, self.stop)))
        if settings.enable_eth and settings.eth_ws_url:
            st = FeedStatus("eth:pending")
            self.feeds["eth"] = st
            self.tasks.append(asyncio.create_task(
                run_eth_pending(on_tx, st, self.stop)))

        # Demo fallback: starts only if no live tx arrives within a grace period.
        if settings.demo_fallback:
            self.tasks.append(asyncio.create_task(self._demo_watchdog(on_tx)))

        # Scoring consumers + periodic adapters
        self.tasks.append(asyncio.create_task(self._scoring_loop()))
        self.tasks.append(asyncio.create_task(self._adapt_loop()))
        log.info("Pipeline started with %d tasks", len(self.tasks))

    async def _demo_watchdog(self, on_tx) -> None:
        await asyncio.sleep(8)  # grace period for live feeds to connect
        if self._live_seen:
            log.info("Live tx feed active — demo source stays idle")
            return
        log.warning("No live tx within grace period — starting demo source")
        st = FeedStatus("demo:synthetic")
        self.feeds["demo"] = st
        await run_demo_source(
            on_tx, st, sanctions.sample(40), settings.demo_inject_sanctions,
            rate_per_sec=4.0, stop=self.stop,
        )

    # --- scoring core -------------------------------------------------------
    async def _scoring_loop(self) -> None:
        while not self.stop.is_set():
            tx = await self.bus.consume()
            self.graph.add(tx)
            verdict = score_transaction(tx, self.graph)
            metrics.record_score(verdict.latency_ms, verdict.level)

            self.hub.broadcast({
                "type": "tx",
                "txid": tx.txid, "chain": tx.chain, "ts": verdict.ts,
                "value": round(tx.value, 6), "value_usd": verdict.value_usd,
                "n_in": tx.n_in, "n_out": tx.n_out,
                "risk": verdict.risk, "level": verdict.level,
                "reason": verdict.reason, "latency_ms": verdict.latency_ms,
                "sanctions_hit": verdict.sanctions_hit,
                "inputs": tx.inputs[:6], "outputs": tx.outputs[:6],
            })

            alert = alert_engine.maybe_alert(tx, verdict, self.graph)
            if alert is not None:
                metrics.alerts += 1
                store.save_alert(alert)
                self.hub.broadcast({"type": "alert", "alert": alert.model_dump()})

    async def _adapt_loop(self) -> None:
        while not self.stop.is_set():
            await asyncio.sleep(2)
            self.bus.adapt_sampling()

    async def shutdown(self) -> None:
        self.stop.set()
        for t in self.tasks:
            t.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)

    # --- health -------------------------------------------------------------
    def health(self) -> dict:
        return {
            "feeds": {k: v.snapshot() for k, v in self.feeds.items()},
            "bus": self.bus.metrics.snapshot(),
            "graph": self.graph.stats(),
            "metrics": metrics.snapshot(),
            "model_version": model.version,
            "model_loaded": model.loaded,
            "anomaly_loaded": anomaly.loaded,
            "sanctions_count": len(sanctions.flagged),
            "sanctions_sources": sanctions.loaded_from,
            "sar_mode": settings.sar_model or "template",
            "sar_last_error": __import__("aegis.alerting.sar", fromlist=["LAST_ERROR"]).LAST_ERROR,
            "clients": self.hub.client_count,
            "sample_rate": round(self.bus.sample_rate, 3),
        }


pipeline = Pipeline()
