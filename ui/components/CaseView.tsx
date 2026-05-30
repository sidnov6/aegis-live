"use client";
import { useEffect, useRef, useState } from "react";
import { levelColor, short } from "@/lib/format";
import { API_BASE } from "@/lib/config";

export default function CaseView({
  alert, onAct,
}: { alert: any; onAct: (id: string, action: string) => Promise<void> }) {
  const [status, setStatus] = useState(alert.status);
  const [sarText, setSarText] = useState(alert.sar_text);
  const [sarSource, setSarSource] = useState(alert.sar_source);
  const [drafting, setDrafting] = useState(false);
  const requested = useRef<string | null>(null);
  const sg = alert.subgraph || { nodes: [], edges: [] };

  const generateSar = async () => {
    setDrafting(true);
    try {
      const r = await fetch(`${API_BASE}/api/sar/${alert.alert_id}`, { method: "POST" });
      const d = await r.json();
      if (d.ok) { setSarText(d.sar_text); setSarSource(d.sar_source); }
    } catch {}
    setDrafting(false);
  };

  // On opening a case, draft the AI SAR on demand (token-efficient — one call per
  // human review). The template SAR is shown instantly meanwhile.
  useEffect(() => {
    setSarText(alert.sar_text);
    setSarSource(alert.sar_source);
    if (requested.current === alert.alert_id) return;
    requested.current = alert.alert_id;
    if (!String(alert.sar_source || "").startsWith("llm")) generateSar();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [alert.alert_id]);

  const handle = async (action: string, newStatus: string) => {
    setStatus(newStatus);
    await onAct(alert.alert_id, action);
  };

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="px-4 py-3 border-b border-edge">
        <div className="flex items-center gap-2">
          <span className={`text-sm font-semibold ${levelColor[alert.level]}`}>
            {alert.level.toUpperCase()} · risk {(alert.risk * 100).toFixed(0)}
          </span>
          <span className="text-[10px] text-muted ml-auto uppercase">case {alert.alert_id}</span>
        </div>
        <div className="text-xs mono text-ink/80 mt-1">{alert.address}</div>
        <div className={`text-xs mt-1 ${levelColor[alert.level]}`}>{alert.reason}</div>
      </div>

      <div className="px-4 py-3 border-b border-edge">
        <div className="text-[10px] uppercase tracking-wider text-muted mb-1">triggering subgraph</div>
        <div className="text-xs text-ink/70">
          {sg.nodes?.length || 0} addresses · {sg.edges?.length || 0} transfers
        </div>
        <div className="mt-2 max-h-28 overflow-y-auto text-[11px] mono space-y-0.5">
          {(sg.nodes || []).slice(0, 12).map((n: any) => (
            <div key={n.id} className="flex items-center gap-2">
              <span className={n.flagged ? "text-sanctioned" : n.subject ? "text-accent" : "text-muted"}>
                {n.flagged ? "⚠" : n.subject ? "◉" : "·"}
              </span>
              <span className="text-ink/70">{short(n.id, 10)}</span>
              {n.flagged && <span className="text-sanctioned text-[10px]">FLAGGED</span>}
            </div>
          ))}
        </div>
      </div>

      <div className="px-4 py-3 flex-1">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[10px] uppercase tracking-wider text-muted">
            drafted SAR · source:{" "}
            <span className={sarSource?.startsWith("llm") ? "text-accent" : "text-muted"}>
              {drafting ? "drafting (AI)…" : sarSource}
            </span>
          </span>
          <button
            onClick={generateSar}
            disabled={drafting}
            className="ml-auto text-[10px] px-2 py-0.5 rounded border border-accent/40 text-accent hover:bg-accent/10 disabled:opacity-40"
          >
            {drafting ? "…" : sarSource?.startsWith("llm") ? "Regenerate AI SAR" : "Generate AI SAR"}
          </button>
        </div>
        <pre className={`text-[11px] whitespace-pre-wrap bg-bg/60 border border-edge rounded p-3 leading-relaxed ${
          drafting ? "text-muted animate-pulse2" : "text-ink/80"
        }`}>
{sarText}
        </pre>
      </div>

      <div className="px-4 py-3 border-t border-edge flex gap-2 sticky bottom-0 bg-panel">
        <button
          onClick={() => handle("approve", "approved")}
          className="px-3 py-1.5 text-xs rounded bg-cleared/20 text-cleared border border-cleared/40 hover:bg-cleared/30"
        >Approve</button>
        <button
          onClick={() => handle("file", "filed")}
          className="px-3 py-1.5 text-xs rounded bg-accent/20 text-accent border border-accent/40 hover:bg-accent/30"
        >File SAR</button>
        <button
          onClick={() => handle("dismiss", "dismissed")}
          className="px-3 py-1.5 text-xs rounded bg-panel2 text-muted border border-edge hover:text-ink"
        >Dismiss</button>
        <span className="ml-auto text-xs self-center text-accent uppercase">{status}</span>
      </div>
    </div>
  );
}
