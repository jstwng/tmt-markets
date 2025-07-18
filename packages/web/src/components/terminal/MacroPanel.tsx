import { useTerminalPanel } from "@/hooks/useTerminalPanel";
import PanelShell from "./PanelShell";
import { cn } from "@/lib/utils";

interface MacroField {
  key: string;
  label: string;
  decimals: number;
  suffix: string;
}

const FIELDS: MacroField[] = [
  { key: "FEDFUNDS", label: "Fed Funds", decimals: 2, suffix: "%" },
  { key: "DGS2", label: "2Y Treasury", decimals: 2, suffix: "%" },
  { key: "DGS10", label: "10Y Treasury", decimals: 2, suffix: "%" },
  { key: "CPIAUCSL", label: "CPI YoY", decimals: 1, suffix: "%" },
  { key: "VIXCLS", label: "VIX", decimals: 1, suffix: "" },
];

function extractSeriesLatest(
  rawData: unknown[],
  symbol: string
): { current: number | null; prev: number | null; sparkline: number[] } {
  if (!Array.isArray(rawData) || rawData.length === 0) {
    return { current: null, prev: null, sparkline: [] };
  }
  const rows = (rawData as Record<string, unknown>[])
    .filter((r) => {
      const sym = (r.symbol ?? r.series_id ?? "") as string;
      return sym === symbol || sym === "";
    })
    .sort((a, b) => {
      const da = (a.date ?? a.timestamp ?? "") as string;
      const db = (b.date ?? b.timestamp ?? "") as string;
      return da.localeCompare(db);
    });

  const values = rows
    .map((r) => parseFloat(String(r.value ?? r.close ?? 0)))
    .filter(isFinite);
  return {
    current: values.length > 0 ? values[values.length - 1] : null,
    prev: values.length > 1 ? values[values.length - 2] : null,
    sparkline: values.slice(-30),
  };
}

function Sparkline({ values }: { values: number[] }) {
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const h = 24;
  const w = 64;
  const pts = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * w;
      const y = h - ((v - min) / range) * h;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const color = values[values.length - 1] >= values[0] ? "#16a34a" : "#dc2626";
  return (
    <svg viewBox={`0 0 ${w} ${h}`} style={{ width: w, height: h }}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" />
    </svg>
  );
}

export default function MacroPanel({ intervalMs }: { intervalMs: number }) {
  const { data, loading, error, lastUpdated, refetch } = useTerminalPanel("macro", intervalMs);
  const rawData: unknown[] = data?.raw_data ?? [];

  return (
    <PanelShell title="Macro" lastUpdated={lastUpdated} error={error} loading={loading} onRetry={refetch}>
      <div className="flex gap-0 overflow-x-auto -mx-4 px-4">
        {FIELDS.map((field, i) => {
          const { current, prev, sparkline } = extractSeriesLatest(rawData, field.key);
          const change = current !== null && prev !== null ? current - prev : null;
          return (
            <div
              key={field.key}
              className={cn(
                "flex-1 min-w-[90px] px-3",
                i < FIELDS.length - 1 && "border-r border-border"
              )}
            >
              <div className="text-xs text-muted-foreground mb-1">{field.label}</div>
              <div className="text-base font-bold">
                {current !== null ? `${current.toFixed(field.decimals)}${field.suffix}` : "—"}
              </div>
              {change !== null && (
                <div
                  className={cn(
                    "text-xs font-medium",
                    change >= 0 ? "text-green-600" : "text-red-600"
                  )}
                >
                  {change >= 0 ? "+" : ""}
                  {change.toFixed(field.decimals)}
                </div>
              )}
              <div className="mt-1">
                <Sparkline values={sparkline} />
              </div>
            </div>
          );
        })}
      </div>
    </PanelShell>
  );
}
