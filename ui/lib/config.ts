// Backend endpoints. Override in production via NEXT_PUBLIC_* env at build time.
export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

export const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ||
  (API_BASE.replace(/^http/, "ws") + "/ws");
