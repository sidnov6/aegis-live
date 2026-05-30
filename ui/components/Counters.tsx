"use client";
import { StreamState } from "@/lib/useStream";
import { num } from "@/lib/format";

function Stat({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent?: string }) {
  return (
    <div className="flex-1 min-w-[130px] bg-surface border border-line rounded-xl px-4 py-3 shadow-card">
      <div className="text-[11px] font-medium uppercase tracking-wide text-muted">{label}</div>
      <div className={`mt-1 text-2xl font-semibold tabular ${accent || "text-fg"}`}>{value}</div>
      {sub && <div className="text-[11px] text-muted mt-0.5">{sub}</div>}
    </div>
  );
}

export default function Counters({ s }: { s: StreamState }) {
  const m = s.health?.metrics || {};
  return (
    <div className="flex gap-3 flex-wrap">
      <Stat label="Throughput" value={`${(m.tx_per_sec ?? 0).toFixed(1)}`} sub="tx / sec" accent="text-accent" />
      <Stat label="Scored" value={num(m.scored ?? 0)} sub="this session" />
      <Stat label="Flagged" value={num(m.flagged ?? 0)} sub="elevated risk" accent="text-warn" />
      <Stat label="Sanctioned" value={num(m.sanctioned_hits ?? 0)} sub="list hits" accent="text-sanction" />
      <Stat label="Alerts" value={num(m.alerts ?? 0)} sub="raised" accent="text-danger" />
      <Stat label="Latency p95" value={`${(m.latency_ms_p95 ?? 0).toFixed(1)}`} sub="ms to score" accent="text-accent" />
    </div>
  );
}
