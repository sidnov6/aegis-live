"use client";
import { useEffect, useRef, useState } from "react";
import { WS_URL } from "./config";

export type Tx = {
  type: "tx";
  txid: string; chain: string; ts: number;
  value: number; value_usd: number; n_in: number; n_out: number;
  risk: number; level: string; reason: string; latency_ms: number;
  sanctions_hit: boolean; inputs: string[]; outputs: string[];
};
export type AlertMsg = { type: "alert"; alert: any };
export type Ticker = { type: "ticker"; symbol: string; price: number; ts: number };
export type Health = { type: "health"; [k: string]: any };

export type StreamState = {
  connected: boolean;
  txs: Tx[];                 // most recent first
  alerts: any[];             // most recent first
  prices: Record<string, { price: number; prev: number }>;
  health: any | null;
  lastSanction: Tx | null;   // for the red-bloom trigger
  sanctionSeq: number;
};

const MAX_TXS = 140;
const MAX_ALERTS = 60;

export function useStream(): StreamState {
  const [state, setState] = useState<StreamState>({
    connected: false, txs: [], alerts: [], prices: {}, health: null,
    lastSanction: null, sanctionSeq: 0,
  });
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    let stop = false;
    let backoff = 500;
    const connect = () => {
      if (stop) return;
      const sock = new WebSocket(WS_URL);
      ws.current = sock;
      sock.onopen = () => {
        backoff = 500;
        setState((s) => ({ ...s, connected: true }));
      };
      sock.onclose = () => {
        setState((s) => ({ ...s, connected: false }));
        if (!stop) setTimeout(connect, Math.min(backoff, 8000));
        backoff *= 2;
      };
      sock.onerror = () => sock.close();
      sock.onmessage = (ev) => {
        let msg: any;
        try { msg = JSON.parse(ev.data); } catch { return; }
        setState((s) => {
          if (msg.type === "tx") {
            const txs = [msg, ...s.txs].slice(0, MAX_TXS);
            const isSanction = msg.level === "sanctioned";
            return {
              ...s, txs,
              lastSanction: isSanction ? msg : s.lastSanction,
              sanctionSeq: isSanction ? s.sanctionSeq + 1 : s.sanctionSeq,
            };
          }
          if (msg.type === "alert") {
            return { ...s, alerts: [msg.alert, ...s.alerts].slice(0, MAX_ALERTS) };
          }
          if (msg.type === "alert_status") {
            return {
              ...s,
              alerts: s.alerts.map((a) =>
                a.alert_id === msg.alert_id ? { ...a, status: msg.status } : a),
            };
          }
          if (msg.type === "ticker") {
            const prev = s.prices[msg.symbol]?.price ?? msg.price;
            return { ...s, prices: { ...s.prices, [msg.symbol]: { price: msg.price, prev } } };
          }
          if (msg.type === "health") {
            return { ...s, health: msg };
          }
          return s;
        });
      };
    };
    connect();
    return () => { stop = true; ws.current?.close(); };
  }, []);

  return state;
}
