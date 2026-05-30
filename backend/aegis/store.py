"""Persistence (Part 6). SQLite by default (zero-config, $0); set DATABASE_URL to
a Postgres URL (Supabase/Neon) for the cloud path. We keep a tiny hand-rolled
layer so there are no heavy ORM deps for the local demo."""
from __future__ import annotations

import json
import os
import sqlite3
import threading

from .conf.settings import settings
from .schema import Alert


class Store:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pg = settings.database_url.startswith("postgres")
        if self._pg:
            self._init_pg()
        else:
            path = settings.database_url.replace("sqlite:///", "")
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            self._conn = sqlite3.connect(path, check_same_thread=False)
            self._init_sqlite()

    def _init_sqlite(self) -> None:
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS alerts (
                alert_id TEXT PRIMARY KEY, txid TEXT, chain TEXT, ts REAL,
                risk REAL, level TEXT, reason TEXT, address TEXT,
                subgraph TEXT, sar_text TEXT, sar_source TEXT, status TEXT)"""
        )
        self._conn.commit()

    def _init_pg(self) -> None:
        import psycopg

        self._conn = psycopg.connect(settings.database_url, autocommit=True)
        with self._conn.cursor() as cur:
            cur.execute(
                """CREATE TABLE IF NOT EXISTS alerts (
                    alert_id TEXT PRIMARY KEY, txid TEXT, chain TEXT, ts DOUBLE PRECISION,
                    risk DOUBLE PRECISION, level TEXT, reason TEXT, address TEXT,
                    subgraph JSONB, sar_text TEXT, sar_source TEXT, status TEXT)"""
            )

    def save_alert(self, a: Alert) -> None:
        row = (
            a.alert_id, a.txid, a.chain, a.ts, a.risk, a.level, a.reason,
            a.address, json.dumps(a.subgraph), a.sar_text, a.sar_source, a.status,
        )
        with self._lock:
            if self._pg:
                with self._conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO alerts VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                           ON CONFLICT (alert_id) DO NOTHING""", row)
            else:
                self._conn.execute(
                    "INSERT OR REPLACE INTO alerts VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", row)
                self._conn.commit()

    def update_status(self, alert_id: str, status: str) -> None:
        with self._lock:
            if self._pg:
                with self._conn.cursor() as cur:
                    cur.execute("UPDATE alerts SET status=%s WHERE alert_id=%s",
                                (status, alert_id))
            else:
                self._conn.execute("UPDATE alerts SET status=? WHERE alert_id=?",
                                   (status, alert_id))
                self._conn.commit()

    def recent_alerts(self, limit: int = 100) -> list[dict]:
        ph = "%s" if self._pg else "?"
        q = f"SELECT alert_id,txid,chain,ts,risk,level,reason,address,subgraph,sar_text,sar_source,status FROM alerts ORDER BY ts DESC LIMIT {ph}"
        with self._lock:
            if self._pg:
                with self._conn.cursor() as cur:
                    cur.execute(q, (limit,))
                    rows = cur.fetchall()
            else:
                rows = self._conn.execute(q, (limit,)).fetchall()
        out = []
        for r in rows:
            sg = r[8]
            out.append({
                "alert_id": r[0], "txid": r[1], "chain": r[2], "ts": r[3],
                "risk": r[4], "level": r[5], "reason": r[6], "address": r[7],
                "subgraph": sg if isinstance(sg, dict) else json.loads(sg or "{}"),
                "sar_text": r[9], "sar_source": r[10], "status": r[11],
            })
        return out


store = Store()
