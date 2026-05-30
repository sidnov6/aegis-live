"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { StreamState } from "@/lib/useStream";
import { useTheme } from "@/lib/theme";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

type GNode = { id: string; level: string; sanctioned: boolean; val: number; seen: number };
type GLink = { source: any; target: any; level: string };

const MAX_NODES = 130;

function palette(dark: boolean) {
  return {
    cleared: dark ? "#2dce9c" : "#0da57a",
    elevated: dark ? "#f5b731" : "#c88a0a",
    high: dark ? "#f87171" : "#e03149",
    sanctioned: dark ? "#f43f6e" : "#db1a5a",
    neutral: dark ? "#7c75ff" : "#635bff",
    link: dark ? "rgba(140,149,173,0.16)" : "rgba(108,117,140,0.18)",
    linkS: dark ? "#f43f6e" : "#db1a5a",
    bg: dark ? "#111524" : "#ffffff",
    label: dark ? "#8c95ad" : "#6c758c",
  };
}
const colorFor = (p: any, level: string) => p[level] || p.neutral;

export default function NetworkGraph({ s, compact }: { s: StreamState; compact?: boolean }) {
  const { theme } = useTheme();
  const dark = theme === "dark";
  const p = useMemo(() => palette(dark), [dark]);

  const wrap = useRef<HTMLDivElement>(null);
  const fg = useRef<any>(null);
  const [dim, setDim] = useState({ w: 600, h: 400 });

  // Persistent graph state — REUSING node objects across updates preserves their
  // simulated positions, so the layout grows smoothly instead of re-exploding.
  const nodes = useRef<Map<string, GNode>>(new Map());
  const links = useRef<GLink[]>([]);
  const txsRef = useRef(s.txs);
  txsRef.current = s.txs;
  const [version, setVersion] = useState(0);

  useEffect(() => {
    const update = () => {
      if (wrap.current) setDim({ w: wrap.current.clientWidth, h: wrap.current.clientHeight });
    };
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  // Throttled, incremental ingest (every 1.1s) — not on every single tx.
  useEffect(() => {
    const tick = () => {
      const recent = txsRef.current.slice(0, 40);
      const nmap = nodes.current;
      let changed = false;
      const touch = (id: string, level: string, sanct: boolean, now: number) => {
        let n = nmap.get(id);
        if (!n) {
          n = { id, level, sanctioned: sanct, val: 1, seen: now };
          nmap.set(id, n);
          changed = true;
        } else {
          n.val = Math.min(10, n.val + 0.4);
          n.seen = now;
          if (sanct) { n.sanctioned = true; n.level = "sanctioned"; }
          else if (n.level === "cleared" && level !== "cleared") n.level = level;
        }
      };
      const now = Date.now();
      for (const tx of recent) {
        const ins = (tx.inputs || []).slice(0, 2);
        const outs = (tx.outputs || []).slice(0, 2);
        [...ins, ...outs].forEach((a) => touch(a, tx.level, tx.level === "sanctioned", now));
        for (const a of ins) for (const b of outs) {
          links.current.push({ source: a, target: b, level: tx.level });
          changed = true;
        }
      }
      // prune to most-recently-seen nodes; drop dangling links
      if (nmap.size > MAX_NODES) {
        const keep = new Set(
          [...nmap.values()].sort((a, b) => b.seen - a.seen).slice(0, MAX_NODES).map((n) => n.id)
        );
        for (const id of [...nmap.keys()]) if (!keep.has(id)) nmap.delete(id);
        changed = true;
      }
      if (links.current.length > 360) links.current = links.current.slice(-360);
      links.current = links.current.filter((l) => {
        const sid = typeof l.source === "object" ? l.source.id : l.source;
        const tid = typeof l.target === "object" ? l.target.id : l.target;
        return nmap.has(sid) && nmap.has(tid);
      });
      if (changed) setVersion((x) => x + 1);
    };
    tick();
    const iv = setInterval(tick, 1100);
    return () => clearInterval(iv);
  }, []);

  // Build the data object with REUSED node refs (identity preserved => positions kept).
  const data = useMemo(
    () => ({ nodes: [...nodes.current.values()], links: links.current }),
    [version]
  );

  return (
    <div ref={wrap} className="w-full h-full relative">
      <div className="absolute top-3 left-3 z-10 text-[11px] text-muted bg-surface/80 backdrop-blur px-2.5 py-1 rounded-lg border border-line">
        rolling graph · <span className="tabular text-fg">{data.nodes.length}</span> addresses
        · <span className="tabular text-fg">{data.links.length}</span> flows
      </div>
      {!compact && (
        <div className="absolute top-3 right-3 z-10 flex items-center gap-3 text-[11px] text-muted bg-surface/80 backdrop-blur px-2.5 py-1 rounded-lg border border-line">
          <span className="flex items-center gap-1"><i className="h-2 w-2 rounded-full" style={{ background: p.cleared }} /> cleared</span>
          <span className="flex items-center gap-1"><i className="h-2 w-2 rounded-full" style={{ background: p.high }} /> high</span>
          <span className="flex items-center gap-1"><i className="h-2 w-2 rounded-full" style={{ background: p.sanctioned }} /> sanctioned</span>
        </div>
      )}
      {/* @ts-ignore */}
      <ForceGraph2D
        ref={fg}
        width={dim.w}
        height={dim.h}
        graphData={data}
        backgroundColor={p.bg}
        nodeRelSize={4}
        nodeVal={(n: any) => 1 + n.val}
        nodeColor={(n: any) => colorFor(p, n.level)}
        nodeLabel={(n: any) => `${n.id}${n.sanctioned ? "  ⚠ sanctioned" : ""}`}
        linkColor={(l: any) => (l.level === "sanctioned" ? p.linkS : p.link)}
        linkWidth={(l: any) => (l.level === "sanctioned" ? 1.4 : 0.6)}
        linkDirectionalParticles={(l: any) => (l.level === "sanctioned" ? 2 : 0)}
        linkDirectionalParticleWidth={2}
        linkDirectionalParticleSpeed={0.006}
        nodeCanvasObjectMode={() => "after"}
        nodeCanvasObject={(n: any, ctx: any, scale: number) => {
          // soft glow for risky nodes
          if (n.level === "sanctioned" || n.level === "high") {
            ctx.beginPath();
            ctx.arc(n.x, n.y, (1 + n.val) * 1.8 + 2, 0, 2 * Math.PI);
            ctx.fillStyle = (n.level === "sanctioned" ? p.sanctioned : p.high) + "22";
            ctx.fill();
          }
          if (n.sanctioned) {
            ctx.beginPath();
            ctx.arc(n.x, n.y, (1 + n.val) * 1.8 + 4, 0, 2 * Math.PI);
            ctx.strokeStyle = p.sanctioned;
            ctx.lineWidth = 1.2 / scale;
            ctx.stroke();
          }
        }}
        cooldownTime={2500}
        warmupTicks={20}
        d3VelocityDecay={0.55}
        d3AlphaDecay={0.045}
        onEngineStop={() => {
          // gently fit the view once it first settles
          if (version <= 2 && fg.current) fg.current.zoomToFit(400, 40);
        }}
      />
    </div>
  );
}
