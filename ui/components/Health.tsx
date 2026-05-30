"use client";
import { StreamState } from "@/lib/useStream";
import { num } from "@/lib/format";

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-panel border border-edge rounded-md p-4">
      <div className="text-[10px] uppercase tracking-wider text-muted mb-2">{title}</div>
      {children}
    </div>
  );
}
function KV({ k, v, color }: { k: string; v: any; color?: string }) {
  return (
    <div className="flex justify-between text-xs py-0.5">
      <span className="text-muted">{k}</span>
      <span className={`tabular-nums ${color || "text-ink"}`}>{String(v)}</span>
    </div>
  );
}

export default function Health({ s }: { s: StreamState }) {
  const h = s.health || {};
  const feeds = h.feeds || {};
  const bus = h.bus || {};
  const m = h.metrics || {};
  return (
    <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 overflow-y-auto p-1">
      <Card title="feeds">
        {Object.keys(feeds).length === 0 && <div className="text-muted text-xs">—</div>}
        {Object.entries(feeds).map(([k, f]: any) => (
          <div key={k} className="mb-2">
            <div className="flex items-center gap-2 text-xs">
              <span className={`h-2 w-2 rounded-full ${
                f.connected ? (f.stale ? "bg-elevated" : "bg-cleared") : "bg-high"}`} />
              <span className="text-ink">{f.name}</span>
              <span className="text-muted ml-auto">
                {f.connected ? (f.stale ? "stale" : "live") : "down"}
              </span>
            </div>
            <KV k="events" v={num(f.events || 0)} />
            <KV k="reconnects" v={f.reconnects || 0} />
            {f.last_error && (
              <div className="text-[10px] text-high/70 truncate">{f.last_error}</div>
            )}
          </div>
        ))}
      </Card>

      <Card title="throughput & latency">
        <KV k="tx / sec" v={(m.tx_per_sec ?? 0).toFixed(2)} color="text-accent" />
        <KV k="scored" v={num(m.scored ?? 0)} />
        <KV k="latency p50" v={`${(m.latency_ms_p50 ?? 0).toFixed(2)} ms`} color="text-scoring" />
        <KV k="latency p95" v={`${(m.latency_ms_p95 ?? 0).toFixed(2)} ms`} color="text-scoring" />
        <KV k="latency p99" v={`${(m.latency_ms_p99 ?? 0).toFixed(2)} ms`} color="text-scoring" />
        <KV k="uptime" v={`${(m.uptime_s ?? 0).toFixed(0)} s`} />
      </Card>

      <Card title="event bus / backpressure">
        <KV k="depth" v={`${bus.depth ?? 0} / ${bus.maxsize ?? 0}`} />
        <KV k="enqueued" v={num(bus.enqueued ?? 0)} />
        <KV k="dropped (backpressure)" v={num(bus.dropped_backpressure ?? 0)} color="text-elevated" />
        <KV k="dropped (sampling)" v={num(bus.dropped_sampling ?? 0)} color="text-elevated" />
        <KV k="sample rate" v={h.sample_rate ?? 1} />
      </Card>

      <Card title="model & scoring">
        <KV k="model version" v={h.model_version || "—"} color="text-accent" />
        <KV k="model loaded" v={h.model_loaded ? "yes" : "fallback"}
            color={h.model_loaded ? "text-cleared" : "text-elevated"} />
        <KV k="anomaly loaded" v={h.anomaly_loaded ? "yes" : "fallback"}
            color={h.anomaly_loaded ? "text-cleared" : "text-elevated"} />
        <KV k="sanctions list" v={num(h.sanctions_count ?? 0)} />
        <KV k="SAR mode" v={h.sar_mode || "template"} />
      </Card>

      <Card title="rolling graph">
        <KV k="nodes" v={num(h.graph?.nodes ?? 0)} />
        <KV k="edges" v={num(h.graph?.edges ?? 0)} />
        <KV k="window" v={`${h.graph?.window_s ?? 0} s`} />
      </Card>

      <Card title="connections">
        <KV k="ws clients" v={h.clients ?? 0} />
        <KV k="flagged" v={num(m.flagged ?? 0)} color="text-elevated" />
        <KV k="sanctioned hits" v={num(m.sanctioned_hits ?? 0)} color="text-sanctioned" />
        <KV k="alerts" v={num(m.alerts ?? 0)} color="text-high" />
      </Card>
    </div>
  );
}
