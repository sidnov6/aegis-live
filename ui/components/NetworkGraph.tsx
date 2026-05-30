"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { StreamState } from "@/lib/useStream";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

type GNode = { id: string; level: string; sanctioned: boolean; val: number };
type GLink = { source: string; target: string; level: string };

// Build a live graph from the recent tx window (nodes age out with the window).
function buildGraph(s: StreamState) {
  const nodes = new Map<string, GNode>();
  const links: GLink[] = [];
  const recent = s.txs.slice(0, 90);
  for (const tx of recent) {
    const ins = tx.inputs?.slice(0, 3) || [];
    const outs = tx.outputs?.slice(0, 3) || [];
    const touch = (id: string) => {
      const n = nodes.get(id);
      const sanct = tx.level === "sanctioned";
      if (!n) nodes.set(id, { id, level: tx.level, sanctioned: sanct, val: 1 });
      else { n.val += 1; if (sanct) { n.sanctioned = true; n.level = "sanctioned"; }
             else if (n.level === "cleared") n.level = tx.level; }
    };
    [...ins, ...outs].forEach(touch);
    for (const a of ins) for (const b of outs)
      links.push({ source: a, target: b, level: tx.level });
  }
  return { nodes: Array.from(nodes.values()), links };
}

const COLORS: Record<string, string> = {
  cleared: "#2ee6a6", elevated: "#f5b942", high: "#ff5a4d", sanctioned: "#ff2b6d",
};

export default function NetworkGraph({ s }: { s: StreamState }) {
  const data = useMemo(() => buildGraph(s), [s.txs]);
  const wrap = useRef<HTMLDivElement>(null);
  const [dim, setDim] = useState({ w: 800, h: 600 });

  useEffect(() => {
    const update = () => {
      if (wrap.current)
        setDim({ w: wrap.current.clientWidth, h: wrap.current.clientHeight });
    };
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  return (
    <div ref={wrap} className="w-full h-full relative">
      <div className="absolute top-3 left-3 z-10 text-xs text-muted bg-panel/80 px-2 py-1 rounded border border-edge">
        live rolling graph · {data.nodes.length} nodes · {data.links.length} edges
      </div>
      {/* @ts-ignore */}
      <ForceGraph2D
        width={dim.w}
        height={dim.h}
        graphData={data}
        backgroundColor="#080b10"
        nodeRelSize={3}
        nodeVal={(n: any) => Math.min(8, n.val)}
        nodeColor={(n: any) => COLORS[n.level] || "#4d9bff"}
        nodeLabel={(n: any) => `${n.id}${n.sanctioned ? " ⚠ SANCTIONED" : ""}`}
        linkColor={(l: any) => (l.level === "sanctioned" ? "#ff2b6d" : "#1c2533")}
        linkWidth={(l: any) => (l.level === "sanctioned" ? 1.6 : 0.4)}
        linkDirectionalParticles={(l: any) => (l.level === "sanctioned" ? 3 : 0)}
        linkDirectionalParticleWidth={2}
        nodeCanvasObjectMode={() => "after"}
        nodeCanvasObject={(n: any, ctx: any) => {
          if (n.sanctioned) {
            ctx.beginPath();
            ctx.arc(n.x, n.y, 7, 0, 2 * Math.PI);
            ctx.strokeStyle = "#ff2b6d";
            ctx.lineWidth = 1.2;
            ctx.stroke();
          }
        }}
        cooldownTicks={80}
      />
    </div>
  );
}
