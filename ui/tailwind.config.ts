import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#080b10",
        panel: "#0d1219",
        panel2: "#111824",
        edge: "#1c2533",
        ink: "#c7d2e0",
        muted: "#5b6878",
        accent: "#19d3da",        // single accent (cyan)
        cleared: "#2ee6a6",       // green
        elevated: "#f5b942",      // amber
        high: "#ff5a4d",          // red
        sanctioned: "#ff2b6d",    // hot red/magenta
        scoring: "#4d9bff",       // blue
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      keyframes: {
        bloom: {
          "0%": { boxShadow: "0 0 0 0 rgba(255,43,109,0.7)" },
          "100%": { boxShadow: "0 0 0 18px rgba(255,43,109,0)" },
        },
        slidein: {
          "0%": { transform: "translateY(-6px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        pulse2: { "50%": { opacity: "0.5" } },
      },
      animation: {
        bloom: "bloom 1.1s ease-out 1",
        slidein: "slidein 0.18s ease-out",
        pulse2: "pulse2 1.6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
export default config;
