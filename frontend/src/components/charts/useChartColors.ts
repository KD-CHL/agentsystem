import { useEffect, useState } from "react";

import { THEME_CHANGE_EVENT } from "../../lib/theme";

export interface ChartColors {
  chart1: string;
  chart2: string;
  chart3: string;
  chart4: string;
  chart5: string;
  chart6: string;
  grid: string;
  axis: string;
  text: string;
  panel: string;
}

function readVar(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  const value = window.getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

function resolve(): ChartColors {
  return {
    chart1: readVar("--chart-1", "#5b8cff"),
    chart2: readVar("--chart-2", "#4cc9e8"),
    chart3: readVar("--chart-3", "#3ecf8e"),
    chart4: readVar("--chart-4", "#e8b84d"),
    chart5: readVar("--chart-5", "#e88a4a"),
    chart6: readVar("--chart-6", "#f26d6f"),
    grid: readVar("--border", "#232936"),
    axis: readVar("--text-faint", "#7c8698"),
    text: readVar("--text-muted", "#a7b0c0"),
    panel: readVar("--panel", "#0e1117"),
  };
}

/**
 * Resolves chart colors from CSS custom properties and re-resolves them
 * whenever the theme changes so charts always match the active palette.
 */
export function useChartColors(): ChartColors {
  const [colors, setColors] = useState<ChartColors>(() => resolve());

  useEffect(() => {
    const refresh = () => setColors(resolve());
    window.addEventListener(THEME_CHANGE_EVENT, refresh);
    return () => window.removeEventListener(THEME_CHANGE_EVENT, refresh);
  }, []);

  return colors;
}
