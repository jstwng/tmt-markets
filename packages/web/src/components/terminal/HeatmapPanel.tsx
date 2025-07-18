import { useTerminalPanel } from "@/hooks/useTerminalPanel";
import PanelShell from "./PanelShell";

const SECTORS = ["XLK", "XLC", "XLY", "XLE", "XLV", "XLF", "XLI", "XLU", "XLRE"];

function dayPctForTicker(rawData: unknown[], ticker: string): number | null {
  const rows = (rawData as Record<string, unknown>[])
    .filter((r) => String(r.symbol ?? r.ticker ?? "") === ticker)
    .sort((a, b) => String(a.date ?? "").localeCompare(String(b.date ?? "")));
  if (rows.length < 2) return null;
  const close = (r: Record<string, unknown>) =>
    parseFloat(String(r.close ?? r.value ?? 0));
  const curr = close(rows[rows.length - 1]);
  const prev = close(rows[rows.length - 2]);
  return prev !== 0 ? (curr - prev) / prev : null;
}

function pctToColor(pct: number | null): { bg: string; text: string } {
  if (pct === null) return { bg: "#f5f5f5", text: "#666" };
  const clamped = Math.max(-0.03, Math.min(0.03, pct));
  const t = (clamped + 0.03) / 0.06; // 0=red, 0.5=white, 1=green
  if (t >= 0.5) {
    const intensity = (t - 0.5) * 2;
    const g = Math.round(200 + intensity * 55);
    const rb = Math.round(200 - intensity * 150);
    return { bg: `rgb(${rb},${g},${rb})`, text: intensity > 0.5 ? "#fff" : "#111" };
  } else {
    const intensity = (0.5 - t) * 2;
    const r = Math.round(200 + intensity * 55);
    const gb = Math.round(200 - intensity * 160);
    return { bg: `rgb(${r},${gb},${gb})`, text: intensity > 0.5 ? "#fff" : "#111" };
  }
}

export default function HeatmapPanel({ intervalMs }: { intervalMs: number }) {
  const { data, loading, error, lastUpdated, refetch } = useTerminalPanel("heatmap", intervalMs);
  const rawData: unknown[] = data?.raw_data ?? [];

  return (
    <PanelShell
      title="Sector Heatmap — Day %"
      lastUpdated={lastUpdated}
      error={error}
      loading={loading}
      onRetry={refetch}
    >
      <div className="grid grid-cols-3 gap-1.5">
        {SECTORS.map((ticker) => {
          const pct = loading ? null : dayPctForTicker(rawData, ticker);
          const { bg, text } = pctToColor(pct);
          return (
            <div
              key={ticker}
              style={{ backgroundColor: loading ? undefined : bg, color: loading ? undefined : text }}
              className={`rounded p-2 text-xs ${loading ? "bg-muted/30 animate-pulse" : ""}`}
            >
              {!loading && (
                <>
                  <div className="font-semibold">{ticker}</div>
                  <div>
                    {pct !== null
                      ? `${pct >= 0 ? "+" : ""}${(pct * 100).toFixed(2)}%`
                      : "—"}
                  </div>
                </>
              )}
            </div>
          );
        })}
      </div>
    </PanelShell>
  );
}
