"use client";
import { StreamState } from "@/lib/useStream";
import { num } from "@/lib/format";

function Stat({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="bg-panel2 border border-edge rounded-md px-4 py-2 min-w-[120px]">
      <div className="text-[10px] uppercase tracking-wider text-muted">{label}</div>
      <div className={`text-xl font-semibold tabular-nums ${accent || "text-ink"}`}>{value}</div>
    </div>
  );
}

export default function Counters({ s }: { s: StreamState }) {
  const m = s.health?.metrics || {};
  return (
    <div className="flex gap-3 flex-wrap">
      <Stat label="tx / sec" value={(m.tx_per_sec ?? 0).toFixed(1)} accent="text-accent" />
      <Stat label="scored" value={num(m.scored ?? 0)} />
      <Stat label="flagged" value={num(m.flagged ?? 0)} accent="text-elevated" />
      <Stat label="sanctioned" value={num(m.sanctioned_hits ?? 0)} accent="text-sanctioned" />
      <Stat label="alerts" value={num(m.alerts ?? 0)} accent="text-high" />
      <Stat label="latency p95" value={`${(m.latency_ms_p95 ?? 0).toFixed(1)}ms`} accent="text-scoring" />
    </div>
  );
}
