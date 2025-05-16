import type { Layout, Config } from "plotly.js";

/**
 * Tufte-inspired Plotly defaults:
 * - No gridlines, no zero lines, no box borders
 * - Thin axis lines, sparse ticks
 * - White background
 * - Responsive width, capped height
 */

export const BASE_LAYOUT: Partial<Layout> = {
  paper_bgcolor: "#ffffff",
  plot_bgcolor: "#ffffff",
  font: {
    family: "Inter, SF Pro Display, system-ui, sans-serif",
    size: 12,
    color: "#111111",
  },
  margin: { l: 52, r: 16, t: 16, b: 48 },
  xaxis: {
    showgrid: false,
    zeroline: false,
    showline: true,
    linecolor: "#e5e5e5",
    linewidth: 1,
    tickcolor: "#e5e5e5",
    ticks: "outside",
    ticklen: 4,
    automargin: true,
  },
  yaxis: {
    showgrid: false,
    zeroline: false,
    showline: false,
    tickcolor: "#e5e5e5",
    ticks: "outside",
    ticklen: 4,
    automargin: true,
  },
  showlegend: false,
  autosize: true,
};

export const BASE_CONFIG: Partial<Config> = {
  displayModeBar: false,
  responsive: true,
};

/** Chart container height in px — keeps charts compact within chat */
export const CHART_HEIGHT = 320;

/** Palette — monochromatic grays with a single accent */
export const PALETTE = {
  primary: "#111111",
  secondary: "#555555",
  muted: "#999999",
  accent: "#2563eb",  // single blue accent for highlights
  positive: "#111111",
  negative: "#555555",
};
