"use client";
import { useState } from "react";
import { StreamState } from "@/lib/useStream";
import { levelColor, levelDot, short, timeAgo } from "@/lib/format";
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

  return (
    <div className="grid grid-cols-2 h-full gap-3">
      <div className="flex flex-col border border-edge rounded-md bg-panel overflow-hidden">
        <div className="px-3 py-2 text-xs uppercase tracking-wider text-muted border-b border-edge">
          ranked alert queue · {alerts.length}
        </div>
        <div className="overflow-y-auto flex-1">
          {alerts.length === 0 && (
            <div className="text-muted text-sm p-6 text-center">no alerts yet</div>
          )}
          {alerts.map((a) => (
            <button
              key={a.alert_id}
              onClick={() => setSelected(a)}
              className={`w-full text-left px-3 py-2 border-b border-edge/60 hover:bg-panel2 ${
                selected?.alert_id === a.alert_id ? "bg-panel2" : ""
              }`}
            >
              <div className="flex items-center gap-2">
                <span className={`h-2 w-2 rounded-full ${levelDot[a.level]}`} />
                <span className={`text-xs font-semibold ${levelColor[a.level]}`}>
                  {(a.risk * 100).toFixed(0)}
                </span>
                <span className="text-xs mono text-ink/80">{short(a.address, 8)}</span>
                <span className="text-[10px] text-muted ml-auto">{timeAgo(a.ts)} ago</span>
                {a.status !== "open" && (
                  <span className="text-[10px] uppercase text-accent">{a.status}</span>
                )}
              </div>
              <div className={`text-xs mt-1 truncate ${levelColor[a.level]}`}>{a.reason}</div>
            </button>
          ))}
        </div>
      </div>
      <div className="border border-edge rounded-md bg-panel overflow-hidden">
        {selected ? (
          <CaseView alert={selected} onAct={act} />
        ) : (
          <div className="text-muted text-sm p-6 text-center">select an alert to view the case</div>
        )}
      </div>
    </div>
  );
}
