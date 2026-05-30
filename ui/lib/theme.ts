"use client";
import { useEffect, useState } from "react";

export type Theme = "light" | "dark";

export function useTheme(): { theme: Theme; toggle: () => void } {
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    const t = (localStorage.getItem("aegis-theme") as Theme) || "light";
    setTheme(t);
    document.documentElement.setAttribute("data-theme", t);
  }, []);

  const toggle = () => {
    setTheme((prev) => {
      const next: Theme = prev === "light" ? "dark" : "light";
      localStorage.setItem("aegis-theme", next);
      document.documentElement.setAttribute("data-theme", next);
      return next;
    });
  };

  return { theme, toggle };
}
