"use client";
import { useState } from "react";
import { StreamState } from "@/lib/useStream";
import { levelColor, levelDot, levelChip, short, timeAgo } from "@/lib/format";
import { API_BASE } from "@/lib/config";
import CaseView from "./CaseView";

async function act(id: string, action: string) {
  try {
    await fetch(`${API_BASE}/api/alerts/${id}/${action}`, { method: "POST" });
  } catch {}
}

export default function AlertConsole({ s }: { s: StreamState }) {
  const [selected, setSelected] = useState<any | null>(null);
  const alerts = [...s.alerts].sort((a, b) => b.risk - a.risk);
  const sel = selected ? s.alerts.find((a) => a.alert_id === selected.alert_id) || selected : null;

  return (
    <div className="grid grid-cols-[380px_1fr] h-full gap-4">
      <div className="flex flex-col bg-surface border border-line rounded-xl shadow-card overflow-hidden">
        <div className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted border-b border-line flex items-center justify-between">
          <span>Alert queue</span>
          <span className="text-fg tabular">{alerts.length}</span>
        </div>
        <div className="overflow-y-auto flex-1">
          {alerts.length === 0 && (
            <div className="text-muted text-sm p-8 text-center">no alerts yet</div>
          )}
          {alerts.map((a) => (
            <button
              key={a.alert_id}
              onClick={() => setSelected(a)}
              className={`w-full text-left px-4 py-3 border-b border-line/70 transition ${
                sel?.alert_id === a.alert_id ? "bg-accent/[0.06]" : "hover:bg-surface2"
              }`}
            >
              <div className="flex items-center gap-2">
                <span className={`h-2 w-2 rounded-full ${levelDot[a.level]}`} />
                <span className={`text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded ${levelChip[a.level]}`}>
                  {a.level}
                </span>
                <span className="text-sm font-semibold tabular text-fg ml-auto">{(a.risk * 100).toFixed(0)}%</span>
              </div>
              <div className="mono text-xs text-fg/70 mt-1.5">{short(a.address, 12)}</div>
              <div className={`text-xs mt-1 line-clamp-2 ${levelColor[a.level]}`}>{a.reason}</div>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-[10px] text-muted">{timeAgo(a.ts)} ago</span>
                {a.status !== "open" && (
                  <span className="text-[10px] font-medium uppercase text-accent ml-auto">{a.status}</span>
                )}
              </div>
            </button>
          ))}
        </div>
      </div>
      <div className="bg-surface border border-line rounded-xl shadow-card overflow-hidden">
        {sel ? (
          <CaseView alert={sel} onAct={act} />
        ) : (
          <div className="text-muted text-sm p-10 text-center">Select an alert to open the case.</div>
        )}
      </div>
    </div>
  );
}
