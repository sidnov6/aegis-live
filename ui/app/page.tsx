"use client";
import { useState } from "react";
import { useStream } from "@/lib/useStream";
import TickerBar from "@/components/Ticker";
import Counters from "@/components/Counters";
import TxFeed from "@/components/TxFeed";
import NetworkGraph from "@/components/NetworkGraph";
import AlertConsole from "@/components/AlertConsole";
import Health from "@/components/Health";
import SanctionBloom from "@/components/SanctionBloom";

type Tab = "wall" | "graph" | "alerts" | "health";
const TABS: { id: Tab; label: string }[] = [
  { id: "wall", label: "The Wall" },
  { id: "graph", label: "Network Graph" },
  { id: "alerts", label: "Alert Console" },
  { id: "health", label: "Stream Health" },
];

export default function Page() {
  const s = useStream();
  const [tab, setTab] = useState<Tab>("wall");
  const openAlerts = s.alerts.filter((a) => a.status === "open").length;

  return (
    <div className="h-screen flex flex-col grid-bg">
      <SanctionBloom s={s} />

      {/* Top bar */}
      <header className="flex items-center gap-4 px-5 py-3 border-b border-edge bg-panel/80 backdrop-blur">
        <div className="flex items-center gap-2">
          <span className="text-accent text-lg font-bold tracking-tight">AEGIS</span>
          <span className="text-muted text-xs uppercase tracking-[0.2em]">live · stromwache</span>
        </div>
        <div className="ml-2">
          <TickerBar s={s} />
        </div>
        <div className="ml-auto flex items-center gap-2 text-xs">
          <span className={`h-2 w-2 rounded-full ${s.connected ? "bg-cleared animate-pulse2" : "bg-high"}`} />
          <span className="text-muted">{s.connected ? "STREAMING" : "RECONNECTING"}</span>
        </div>
      </header>

      {/* Tabs */}
      <nav className="flex items-center gap-1 px-4 py-2 border-b border-edge">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-3 py-1.5 text-xs rounded-md transition-colors ${
              tab === t.id ? "bg-accent/15 text-accent" : "text-muted hover:text-ink"
            }`}
          >
            {t.label}
            {t.id === "alerts" && openAlerts > 0 && (
              <span className="ml-2 px-1.5 rounded-full bg-high/20 text-high text-[10px]">
                {openAlerts}
              </span>
            )}
          </button>
        ))}
      </nav>

      {/* Body */}
      <main className="flex-1 overflow-hidden p-4">
        {tab === "wall" && (
          <div className="h-full flex flex-col gap-4">
            <Counters s={s} />
            <div className="flex-1 grid grid-cols-3 gap-4 overflow-hidden">
              <div className="col-span-2 border border-edge rounded-md bg-panel overflow-hidden flex flex-col">
                <div className="px-3 py-2 text-xs uppercase tracking-wider text-muted border-b border-edge flex justify-between">
                  <span>live transaction stream</span>
                  <span className="text-accent">scored in real time · predictions pending review</span>
                </div>
                <div className="flex-1 overflow-hidden">
                  <TxFeed s={s} />
                </div>
              </div>
              <div className="border border-edge rounded-md bg-panel overflow-hidden">
                <NetworkGraph s={s} />
              </div>
            </div>
          </div>
        )}
        {tab === "graph" && (
          <div className="h-full border border-edge rounded-md bg-panel overflow-hidden">
            <NetworkGraph s={s} />
          </div>
        )}
        {tab === "alerts" && <AlertConsole s={s} />}
        {tab === "health" && <Health s={s} />}
      </main>

      <footer className="px-5 py-1.5 border-t border-edge text-[10px] text-muted flex justify-between">
        <span>
          Live risk scores are PREDICTIONS pending human review. Only sanctions exact-hits are ground-truth designations.
        </span>
        <span>model: {s.health?.model_version || "—"} · sar: {s.health?.sar_mode || "—"}</span>
      </footer>
    </div>
  );
}
