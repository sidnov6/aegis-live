import type { Config } from "tailwindcss";

// Colors are CSS variables (RGB channels) so the same classes flip between the
// light and dark themes. Opacity modifiers work via the <alpha-value> hook.
const v = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

const config: Config = {
  darkMode: ["class", '[data-theme="dark"]'],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: v("bg"),
        surface: v("surface"),
        surface2: v("surface-2"),
        line: v("line"),
        fg: v("fg"),
        muted: v("muted"),
        accent: v("accent"),
        accentSoft: v("accent-soft"),
        pos: v("pos"),
        neg: v("neg"),
        warn: v("warn"),
        danger: v("danger"),
        sanction: v("sanction"),
      },
      fontFamily: {
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      borderRadius: { xl: "0.75rem", "2xl": "1rem" },
      boxShadow: {
        card: "0 1px 2px rgb(16 24 40 / 0.04), 0 1px 3px rgb(16 24 40 / 0.06)",
        cardhover: "0 4px 12px rgb(16 24 40 / 0.08), 0 2px 6px rgb(16 24 40 / 0.06)",
        pop: "0 12px 32px rgb(16 24 40 / 0.12)",
      },
      keyframes: {
        bloom: {
          "0%": { boxShadow: "0 0 0 0 rgb(var(--sanction) / 0.5)" },
          "100%": { boxShadow: "0 0 0 22px rgb(var(--sanction) / 0)" },
        },
        rowin: {
          "0%": { transform: "translateY(-4px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        breathe: { "50%": { opacity: "0.45" } },
        shimmer: { "100%": { transform: "translateX(100%)" } },
      },
      animation: {
        bloom: "bloom 1.2s ease-out 1",
        rowin: "rowin 0.16s ease-out",
        breathe: "breathe 1.8s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
export default config;
