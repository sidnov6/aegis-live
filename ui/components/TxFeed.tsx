"use client";
import { StreamState, Tx } from "@/lib/useStream";
import { levelColor, levelDot, levelBorder, short, usd } from "@/lib/format";

function Row({ tx }: { tx: Tx }) {
  return (
    <div
      className={`flex items-center gap-3 px-3 py-1.5 border-l-2 ${
        levelBorder[tx.level] || "border-l-edge"
      } ${tx.level === "sanctioned" ? "bg-sanctioned/10 animate-bloom" : "hover:bg-panel2"} animate-slidein`}
    >
      <span className={`h-2 w-2 rounded-full ${levelDot[tx.level]} shrink-0`} />
      <span className="text-muted text-xs w-10 shrink-0">{tx.chain}</span>
      <span className="text-ink/80 text-xs w-32 shrink-0 mono truncate">{short(tx.txid, 8)}</span>
      <span className="text-xs w-28 shrink-0 mono text-muted truncate">
        {short(tx.inputs?.[0] || "—", 5)} → {short(tx.outputs?.[0] || "—", 5)}
      </span>
      <span className="text-xs w-16 shrink-0 text-right tabular-nums text-ink/70">
        {usd(tx.value_usd)}
      </span>
      <span className={`text-xs w-12 shrink-0 text-right tabular-nums font-semibold ${levelColor[tx.level]}`}>
        {(tx.risk * 100).toFixed(0)}
      </span>
      <span className="text-[10px] text-muted w-14 shrink-0 text-right tabular-nums">
        {tx.latency_ms.toFixed(1)}ms
      </span>
      <span className={`text-xs flex-1 truncate ${tx.level === "cleared" ? "text-muted" : levelColor[tx.level]}`}>
        {tx.reason}
      </span>
    </div>
  );
}

export default function TxFeed({ s }: { s: StreamState }) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-3 px-3 py-2 text-[10px] uppercase tracking-wider text-muted border-b border-edge">
        <span className="w-2" /> <span className="w-10">chain</span>
        <span className="w-32">txid</span> <span className="w-28">flow</span>
        <span className="w-16 text-right">value</span>
        <span className="w-12 text-right">risk</span>
        <span className="w-14 text-right">latency</span>
        <span className="flex-1">verdict</span>
      </div>
      <div className="overflow-y-auto flex-1">
        {s.txs.length === 0 && (
          <div className="text-muted text-sm p-6 text-center animate-pulse2">
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
