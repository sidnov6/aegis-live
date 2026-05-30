"use client";
import { useEffect, useState } from "react";
import { StreamState } from "@/lib/useStream";
import { short } from "@/lib/format";

// Full-screen red bloom + banner when a sanctioned tx lands (Part 9 "red bloom").
export default function SanctionBloom({ s }: { s: StreamState }) {
  const [show, setShow] = useState(false);
  useEffect(() => {
    if (s.sanctionSeq === 0) return;
    setShow(true);
    const t = setTimeout(() => setShow(false), 2600);
    return () => clearTimeout(t);
  }, [s.sanctionSeq]);

  if (!show || !s.lastSanction) return null;
  const tx = s.lastSanction;
  return (
    <div className="pointer-events-none fixed inset-0 z-50">
      <div className="absolute inset-0 ring-[6px] ring-inset ring-sanctioned/70 animate-bloom" />
      <div className="absolute inset-0 bg-sanctioned/5" />
      <div className="absolute top-6 left-1/2 -translate-x-1/2 bg-sanctioned text-bg font-semibold px-4 py-2 rounded shadow-lg text-sm animate-slidein">
        ⚠ SANCTIONS HIT · {short(tx.txid, 8)} · {tx.reason}
      </div>
    </div>
  );
}
