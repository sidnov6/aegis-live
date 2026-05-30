"use client";
import { StreamState } from "@/lib/useStream";

export default function TickerBar({ s }: { s: StreamState }) {
  const syms = ["BTCUSDT", "ETHUSDT"];
  return (
    <div className="flex items-center gap-5">
      {syms.map((sym) => {
        const p = s.prices[sym];
        const up = p ? p.price >= p.prev : true;
        const label = sym.replace("USDT", "");
        return (
          <div key={sym} className="flex items-center gap-2">
            <span className="text-xs font-medium text-muted">{label}</span>
            <span className="text-sm font-semibold tabular text-fg">
              {p ? `$${p.price.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : "—"}
            </span>
            {p && (
              <span className={`text-[11px] font-medium ${up ? "text-pos" : "text-danger"}`}>
                {up ? "▲" : "▼"}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
