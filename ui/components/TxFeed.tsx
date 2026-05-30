"use client";
import { StreamState, Tx } from "@/lib/useStream";
import { levelColor, levelDot, levelChip, short, usd } from "@/lib/format";

function Row({ tx }: { tx: Tx }) {
  const sanctioned = tx.level === "sanctioned";
  return (
    <div
      className={`grid grid-cols-[16px_44px_1fr_120px_84px_64px_72px] items-center gap-3 px-4 py-2 border-b border-line/70 animate-rowin ${
        sanctioned ? "bg-sanction/[0.06]" : "hover:bg-surface2"
      }`}
    >
      <span className={`h-2 w-2 rounded-full ${levelDot[tx.level]}`} />
      <span className="text-[11px] font-medium text-muted">{tx.chain}</span>
      <span className="mono text-xs text-fg/80 truncate">{short(tx.txid, 10)}</span>
      <span className="mono text-[11px] text-muted truncate">
        {short(tx.inputs?.[0] || "—", 5)} → {short(tx.outputs?.[0] || "—", 5)}
      </span>
      <span className="text-xs text-right tabular text-fg/80">{usd(tx.value_usd)}</span>
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
      <div className="grid grid-cols-[16px_44px_1fr_120px_84px_64px_72px] gap-3 px-4 py-2 text-[10px] font-semibold uppercase tracking-wide text-muted border-b border-line">
        <span /><span>Chain</span><span>Transaction</span><span>Flow</span>
        <span className="text-right">Value</span><span className="text-right">Risk</span>
        <span className="text-right">Latency</span>
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
