"use client";
import { useEffect, useRef, useState } from "react";
import { levelChip, levelColor, short } from "@/lib/format";
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
  const isLlm = String(sarSource || "").startsWith("llm");

  const generateSar = async () => {
    setDrafting(true);
    try {
      const r = await fetch(`${API_BASE}/api/sar/${alert.alert_id}`, { method: "POST" });
      const d = await r.json();
      if (d.ok) { setSarText(d.sar_text); setSarSource(d.sar_source); }
    } catch {}
    setDrafting(false);
  };

  // On opening a case, draft the AI SAR on demand (one LLM call per human review).
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

  const Btn = ({ onClick, children, variant }: any) => (
    <button onClick={onClick}
      className={
        variant === "primary"
          ? "px-3.5 py-2 text-xs font-medium rounded-lg bg-accent text-white hover:opacity-90 transition"
          : variant === "ok"
          ? "px-3.5 py-2 text-xs font-medium rounded-lg bg-pos/10 text-pos border border-pos/30 hover:bg-pos/20 transition"
          : "px-3.5 py-2 text-xs font-medium rounded-lg border border-line text-muted hover:text-fg hover:bg-surface2 transition"
      }>
      {children}
    </button>
  );

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="px-5 py-4 border-b border-line">
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded ${levelChip[alert.level]}`}>
            {alert.level}
          </span>
          <span className="text-sm font-semibold tabular text-fg">risk {(alert.risk * 100).toFixed(0)}%</span>
          <span className="text-[11px] text-muted ml-auto uppercase tracking-wide">case {alert.alert_id}</span>
        </div>
        <div className="mono text-xs text-fg/80 mt-2">{alert.address}</div>
        <div className={`text-xs mt-1 ${levelColor[alert.level]}`}>{alert.reason}</div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="px-5 py-4 border-b border-line">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-muted mb-2">
            Triggering subgraph · {sg.nodes?.length || 0} addresses · {sg.edges?.length || 0} transfers
          </div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
            {(sg.nodes || []).slice(0, 12).map((n: any) => (
              <div key={n.id} className="flex items-center gap-2 text-[11px]">
                <span className={n.flagged ? "text-sanction" : n.subject ? "text-accent" : "text-muted"}>
                  {n.flagged ? "⚠" : n.subject ? "◉" : "·"}
                </span>
                <span className="mono text-fg/70 truncate">{short(n.id, 10)}</span>
                {n.flagged && <span className="text-sanction text-[10px] font-medium">FLAGGED</span>}
              </div>
            ))}
          </div>
        </div>

        <div className="px-5 py-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-muted">
              Suspicious Activity Report
            </span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded ${isLlm ? "bg-accent/10 text-accent" : "bg-surface2 text-muted"}`}>
              {drafting ? "drafting…" : isLlm ? "AI-drafted" : "template"}
            </span>
            <button onClick={generateSar} disabled={drafting}
              className="ml-auto text-[11px] font-medium px-2.5 py-1 rounded-lg border border-accent/40 text-accent hover:bg-accent/10 disabled:opacity-40 transition">
              {drafting ? "…" : isLlm ? "Regenerate" : "Generate AI SAR"}
            </button>
          </div>
          <pre className={`text-[11px] whitespace-pre-wrap rounded-lg border border-line p-4 leading-relaxed font-sans ${
            drafting ? "text-muted shimmer" : "text-fg/80 bg-surface2"
          }`}>
{sarText}
          </pre>
        </div>
      </div>

      <div className="px-5 py-3 border-t border-line flex items-center gap-2 bg-surface">
        <Btn variant="ok" onClick={() => handle("approve", "approved")}>Approve</Btn>
        <Btn variant="primary" onClick={() => handle("file", "filed")}>File SAR</Btn>
        <Btn onClick={() => handle("dismiss", "dismissed")}>Dismiss</Btn>
        <span className="ml-auto text-[11px] font-medium uppercase tracking-wide text-accent">{status}</span>
      </div>
    </div>
  );
}
