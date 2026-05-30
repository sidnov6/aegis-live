export const levelColor: Record<string, string> = {
  cleared: "text-pos",
  elevated: "text-warn",
  high: "text-danger",
  sanctioned: "text-sanction",
};
export const levelDot: Record<string, string> = {
  cleared: "bg-pos",
  elevated: "bg-warn",
  high: "bg-danger",
  sanctioned: "bg-sanction",
};
export const levelBorder: Record<string, string> = {
  cleared: "border-l-pos",
  elevated: "border-l-warn",
  high: "border-l-danger",
  sanctioned: "border-l-sanction",
};
export const levelChip: Record<string, string> = {
  cleared: "bg-pos/10 text-pos",
  elevated: "bg-warn/10 text-warn",
  high: "bg-danger/10 text-danger",
  sanctioned: "bg-sanction/10 text-sanction",
};

export function short(addr: string, n = 6): string {
  if (!addr) return "—";
  if (addr.length <= n * 2 + 1) return addr;
  return `${addr.slice(0, n)}…${addr.slice(-4)}`;
}
export function usd(n: number): string {
  if (!n) return "$0";
  if (n >= 1e6) return `$${(n / 1e6).toFixed(2)}M`;
  if (n >= 1e3) return `$${(n / 1e3).toFixed(1)}k`;
  return `$${n.toFixed(0)}`;
}
export function num(n: number): string {
  return new Intl.NumberFormat("en-US").format(n);
}
export function timeAgo(ts: number): string {
  const s = Math.max(0, Date.now() / 1000 - ts);
  if (s < 60) return `${s.toFixed(0)}s`;
  if (s < 3600) return `${(s / 60).toFixed(0)}m`;
  return `${(s / 3600).toFixed(0)}h`;
}
