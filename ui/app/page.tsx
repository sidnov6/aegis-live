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
import ThemeToggle from "@/components/ThemeToggle";

type Tab = "wall" | "graph" | "alerts" | "health";
const TABS: { id: Tab; label: string }[] = [
  { id: "wall", label: "The Wall" },
  { id: "graph", label: "Network" },
  { id: "alerts", label: "Alerts" },
  { id: "health", label: "Health" },
];

function Panel({ title, right, children, pad }: any) {
  return (
    <div className="flex flex-col bg-surface border border-line rounded-xl shadow-card overflow-hidden h-full">
      <div className="px-4 py-2.5 border-b border-line flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted">{title}</span>
        {right}
      </div>
      <div className={`flex-1 overflow-hidden ${pad ? "p-0" : ""}`}>{children}</div>
    </div>
  );
}

export default function Page() {
  const s = useStream();
  const [tab, setTab] = useState<Tab>("wall");
  const openAlerts = s.alerts.filter((a) => a.status === "open").length;

  return (
    <div className="h-screen flex flex-col">
      <SanctionBloom s={s} />

      {/* Header */}
      <header className="flex items-center gap-4 px-5 h-14 border-b border-line bg-surface/90 backdrop-blur sticky top-0 z-20">
        <div className="flex items-center gap-2.5">
          <span className="h-7 w-7 rounded-lg brand-gradient grid place-items-center text-white text-sm font-bold">A</span>
          <div className="leading-tight">
            <div className="text-sm font-semibold text-fg">AEGIS <span className="text-muted font-normal">Live</span></div>
            <div className="text-[10px] text-muted uppercase tracking-[0.15em]">chain surveillance</div>
          </div>
        </div>
        <div className="hidden sm:block h-6 w-px bg-line mx-1" />
        <TickerBar s={s} />
        <div className="ml-auto flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs">
            <span className={`h-2 w-2 rounded-full ${s.connected ? "bg-pos animate-breathe" : "bg-danger"}`} />
            <span className="text-muted font-medium">{s.connected ? "Streaming" : "Reconnecting"}</span>
          </div>
          <ThemeToggle />
        </div>
      </header>

      {/* Tabs */}
      <nav className="flex items-center gap-1 px-4 py-2 border-b border-line bg-surface">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-3.5 py-1.5 text-sm font-medium rounded-lg transition ${
              tab === t.id ? "bg-accent/10 text-accent" : "text-muted hover:text-fg hover:bg-surface2"
            }`}
          >
            {t.label}
            {t.id === "alerts" && openAlerts > 0 && (
              <span className="ml-2 px-1.5 py-0.5 rounded-full bg-danger/10 text-danger text-[10px] font-semibold">
                {openAlerts}
              </span>
            )}
          </button>
        ))}
      </nav>

      {/* Body */}
      <main className="flex-1 overflow-hidden p-4 bg-bg">
        {tab === "wall" && (
          <div className="h-full flex flex-col gap-4">
            <Counters s={s} />
            <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 overflow-hidden">
              <div className="lg:col-span-2 min-h-0">
                <Panel
                  title="Live transaction stream"
                  right={<span className="text-[11px] text-accent font-medium">scored in real time</span>}
                >
                  <TxFeed s={s} />
                </Panel>
              </div>
              <div className="min-h-0">
                <Panel title="Network">
                  <NetworkGraph s={s} compact />
                </Panel>
              </div>
            </div>
          </div>
        )}
        {tab === "graph" && (
          <div className="h-full">
            <Panel title="Live rolling transaction graph">
              <NetworkGraph s={s} />
            </Panel>
          </div>
        )}
        {tab === "alerts" && <AlertConsole s={s} />}
        {tab === "health" && <Health s={s} />}
      </main>

      <footer className="px-5 py-2 border-t border-line bg-surface flex items-center justify-between text-[11px] text-muted">
        <span>
          Live risk scores are <span className="text-fg">predictions pending human review</span>. Only sanctions exact-hits are ground-truth designations.
        </span>
        <span className="hidden sm:inline">model: {s.health?.model_version || "—"} · SAR: {s.health?.sar_mode || "—"}</span>
      </footer>
    </div>
  );
}
