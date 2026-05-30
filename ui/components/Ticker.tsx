"use client";
import { StreamState } from "@/lib/useStream";

export default function TickerBar({ s }: { s: StreamState }) {
  const syms = ["BTCUSDT", "ETHUSDT"];
  return (
    <div className="flex items-center gap-6">
      {syms.map((sym) => {
        const p = s.prices[sym];
        const up = p ? p.price >= p.prev : true;
        const label = sym.replace("USDT", "/USD");
        return (
          <div key={sym} className="flex items-baseline gap-2">
            <span className="text-muted text-xs">{label}</span>
            <span
              className={`text-lg font-semibold tabular-nums transition-colors ${
                p ? (up ? "text-cleared" : "text-high") : "text-muted"
              }`}
            >
              {p ? `$${p.price.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : "—"}
            </span>
            {p && <span className={up ? "text-cleared" : "text-high"}>{up ? "▲" : "▼"}</span>}
          </div>
        );
      })}
    </div>
  );
}
