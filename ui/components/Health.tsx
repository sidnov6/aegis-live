"use client";
import { StreamState } from "@/lib/useStream";
import { num } from "@/lib/format";

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-surface border border-line rounded-xl p-4 shadow-card">
      <div className="text-[11px] font-semibold uppercase tracking-wide text-muted mb-3">{title}</div>
      {children}
    </div>
  );
}
function KV({ k, v, color }: { k: string; v: any; color?: string }) {
  return (
    <div className="flex justify-between text-xs py-1 border-b border-line/50 last:border-0">
      <span className="text-muted">{k}</span>
      <span className={`tabular font-medium ${color || "text-fg"}`}>{String(v)}</span>
    </div>
  );
}

export default function Health({ s }: { s: StreamState }) {
  const h = s.health || {};
  const feeds = h.feeds || {};
  const bus = h.bus || {};
  const m = h.metrics || {};
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 overflow-y-auto pb-2">
      <Card title="Feeds">
        {Object.keys(feeds).length === 0 && <div className="text-muted text-xs">—</div>}
        {Object.entries(feeds).map(([k, f]: any) => (
          <div key={k} className="mb-3 last:mb-0">
            <div className="flex items-center gap-2 text-xs mb-1">
              <span className={`h-2 w-2 rounded-full ${
                f.connected ? (f.stale ? "bg-warn" : "bg-pos") : "bg-danger"}`} />
              <span className="text-fg font-medium">{f.name}</span>
              <span className="text-muted ml-auto">
                {f.connected ? (f.stale ? "stale" : "live") : "down"}
              </span>
            </div>
            <KV k="events" v={num(f.events || 0)} />
            <KV k="reconnects" v={f.reconnects || 0} />
          </div>
        ))}
      </Card>

      <Card title="Throughput & latency">
        <KV k="tx / sec" v={(m.tx_per_sec ?? 0).toFixed(2)} color="text-accent" />
        <KV k="scored" v={num(m.scored ?? 0)} />
        <KV k="latency p50" v={`${(m.latency_ms_p50 ?? 0).toFixed(2)} ms`} color="text-accent" />
        <KV k="latency p95" v={`${(m.latency_ms_p95 ?? 0).toFixed(2)} ms`} color="text-accent" />
        <KV k="latency p99" v={`${(m.latency_ms_p99 ?? 0).toFixed(2)} ms`} color="text-accent" />
        <KV k="uptime" v={`${(m.uptime_s ?? 0).toFixed(0)} s`} />
      </Card>

      <Card title="Event bus · backpressure">
        <KV k="depth" v={`${bus.depth ?? 0} / ${bus.maxsize ?? 0}`} />
        <KV k="enqueued" v={num(bus.enqueued ?? 0)} />
        <KV k="dropped (backpressure)" v={num(bus.dropped_backpressure ?? 0)} color="text-warn" />
        <KV k="dropped (sampling)" v={num(bus.dropped_sampling ?? 0)} color="text-warn" />
        <KV k="sample rate" v={h.sample_rate ?? 1} />
      </Card>

      <Card title="Model & scoring">
        <KV k="model version" v={h.model_version || "—"} color="text-accent" />
        <KV k="model loaded" v={h.model_loaded ? "yes" : "fallback"}
            color={h.model_loaded ? "text-pos" : "text-warn"} />
        <KV k="anomaly loaded" v={h.anomaly_loaded ? "yes" : "fallback"}
            color={h.anomaly_loaded ? "text-pos" : "text-warn"} />
        <KV k="sanctions list" v={num(h.sanctions_count ?? 0)} />
        <KV k="SAR mode" v={h.sar_mode || "template"} />
      </Card>

      <Card title="Rolling graph">
        <KV k="nodes" v={num(h.graph?.nodes ?? 0)} />
        <KV k="edges" v={num(h.graph?.edges ?? 0)} />
        <KV k="window" v={`${h.graph?.window_s ?? 0} s`} />
      </Card>

      <Card title="Detection">
        <KV k="ws clients" v={h.clients ?? 0} />
        <KV k="flagged" v={num(m.flagged ?? 0)} color="text-warn" />
        <KV k="sanctioned hits" v={num(m.sanctioned_hits ?? 0)} color="text-sanction" />
        <KV k="alerts" v={num(m.alerts ?? 0)} color="text-danger" />
      </Card>
    </div>
  );
}
