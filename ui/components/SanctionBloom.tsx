"use client";
import { useEffect, useState } from "react";
import { StreamState } from "@/lib/useStream";
import { short } from "@/lib/format";

// A refined toast + soft ring when a sanctioned tx lands (no neon flash).
export default function SanctionBloom({ s }: { s: StreamState }) {
  const [show, setShow] = useState(false);
  useEffect(() => {
    if (s.sanctionSeq === 0) return;
    setShow(true);
    const t = setTimeout(() => setShow(false), 3000);
    return () => clearTimeout(t);
  }, [s.sanctionSeq]);

  if (!show || !s.lastSanction) return null;
  const tx = s.lastSanction;
  return (
    <div className="pointer-events-none fixed inset-0 z-50">
      <div className="absolute inset-0 ring-2 ring-inset ring-sanction/40 animate-bloom" />
      <div className="absolute top-5 left-1/2 -translate-x-1/2 flex items-center gap-3 bg-surface border border-sanction/40 shadow-pop rounded-xl px-4 py-2.5 animate-rowin">
        <span className="h-2.5 w-2.5 rounded-full bg-sanction animate-breathe" />
        <div>
          <div className="text-xs font-semibold text-sanction">Sanctions hit detected</div>
          <div className="text-[11px] text-muted mono">{short(tx.txid, 10)} · {tx.reason}</div>
        </div>
      </div>
    </div>
  );
}
