"use client";
import { StreamState, Tx } from "@/lib/useStream";
import { levelColor, levelDot, short, usd } from "@/lib/format";

const COLS = "grid-cols-[14px_40px_minmax(0,1fr)_76px_120px_52px_60px]";

function Bar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="flex items-center gap-1" title={`${label}: ${value.toFixed(3)}`}>
      <span className="text-[9px] text-muted w-2.5">{label}</span>
      <div className="flex-1 h-1.5 rounded-full bg-line/60 overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${Math.max(2, value * 100)}%`, background: color }} />
      </div>
    </div>
  );
}

function Row({ tx }: { tx: Tx }) {
  const sanctioned = tx.level === "sanctioned";
  return (
    <div
      className={`grid ${COLS} items-center gap-3 px-4 py-2 border-b border-line/70 animate-rowin ${
        sanctioned ? "bg-sanction/[0.06]" : "hover:bg-surface2"
      }`}
    >
      <span className={`h-2 w-2 rounded-full ${levelDot[tx.level]}`} />
      <span className="text-[11px] font-medium text-muted">{tx.chain}</span>
      <span className="mono text-xs text-fg/80 truncate">{short(tx.txid, 12)}</span>
      <span className="text-xs text-right tabular text-fg/80">{usd(tx.value_usd)}</span>
      <div className="flex flex-col gap-1">
        <Bar label="M" value={tx.model_score ?? 0} color="rgb(var(--accent))" />
        <Bar label="A" value={tx.anomaly_score ?? 0} color="rgb(var(--warn))" />
      </div>
      <span className={`text-xs text-right tabular font-semibold ${levelColor[tx.level]}`}>
        {(tx.risk * 100).toFixed(0)}%
      </span>
      <span className="text-[11px] text-right tabular text-muted">{tx.latency_ms.toFixed(1)}ms</span>
    </div>
  );
}

export default function TxFeed({ s }: { s: StreamState }) {
  return (
    <div className="flex flex-col h-full">
      <div className={`grid ${COLS} gap-3 px-4 py-2 text-[10px] font-semibold uppercase tracking-wide text-muted border-b border-line`}>
        <span /><span>Chain</span><span>Transaction</span>
        <span className="text-right">Value</span>
        <span>Model · Anomaly</span>
        <span className="text-right">Risk</span>
        <span className="text-right">Lat</span>
      </div>
      <div className="overflow-y-auto flex-1">
        {s.txs.length === 0 && (
          <div className="text-muted text-sm p-8 text-center animate-breathe">
            awaiting live transactions…
          </div>
        )}
        {s.txs.map((tx) => (
          <Row key={tx.txid + tx.ts} tx={tx} />
        ))}
      </div>
    </div>
  );
}
