import { useTerminalPanel } from "@/hooks/useTerminalPanel";
import PanelShell from "./PanelShell";
import { cn } from "@/lib/utils";

const MAJOR = ["SPY", "QQQ", "IWM", "DIA"];
const SECTORS = ["XLK", "XLF", "XLE", "XLV", "XLY", "XLC"];
const ALL_TICKERS = [...MAJOR, ...SECTORS];

function Sparkline5({ values }: { values: number[] }) {
  if (values.length < 2) return <div className="w-10 h-4" />;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const h = 16;
  const w = 40;
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

function buildRows(rawData: unknown[]) {
  if (!Array.isArray(rawData) || rawData.length === 0) {
    return ALL_TICKERS.map((t) => ({
      ticker: t,
      price: null as number | null,
      dayPct: null as number | null,
      sparkline: [] as number[],
      isSector: SECTORS.includes(t),
    }));
  }

  const byTicker: Record<string, Record<string, unknown>[]> = {};
  for (const row of rawData as Record<string, unknown>[]) {
    const ticker = String(row.symbol ?? row.ticker ?? "");
    if (!byTicker[ticker]) byTicker[ticker] = [];
    byTicker[ticker].push(row);
  }

  return ALL_TICKERS.map((ticker) => {
    const rows = (byTicker[ticker] ?? []).sort((a, b) =>
      String(a.date ?? "").localeCompare(String(b.date ?? ""))
    );
    const closes = rows
      .map((r) => parseFloat(String(r.close ?? r.value ?? 0)))
      .filter(isFinite);
    const price = closes.length > 0 ? closes[closes.length - 1] : null;
    const prev = closes.length > 1 ? closes[closes.length - 2] : null;
    const dayPct = price !== null && prev !== null && prev !== 0 ? (price - prev) / prev : null;
    return { ticker, price, dayPct, sparkline: closes.slice(-5), isSector: SECTORS.includes(ticker) };
  });
}

export default function IndicesPanel({ intervalMs }: { intervalMs: number }) {
  const { data, loading, error, lastUpdated, refetch } = useTerminalPanel("indices", intervalMs);
  const rows = buildRows(data?.raw_data ?? []);

  return (
    <PanelShell title="Equity Indices" lastUpdated={lastUpdated} error={error} loading={loading} onRetry={refetch}>
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr className="border-b border-border">
            <th className="text-left py-1.5 font-medium text-muted-foreground">ETF</th>
            <th className="text-right py-1.5 font-medium text-muted-foreground">Price</th>
            <th className="text-right py-1.5 font-medium text-muted-foreground">Day</th>
            <th className="text-right py-1.5 font-medium text-muted-foreground">5D</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.ticker} className="border-b border-border/40 last:border-0">
              <td className={cn("py-2 font-semibold", row.isSector && "text-muted-foreground")}>
                {row.ticker}
              </td>
              <td className={cn("text-right py-2", row.isSector && "text-muted-foreground")}>
                {row.price !== null ? `$${row.price.toFixed(2)}` : "—"}
              </td>
              <td
                className={cn(
                  "text-right py-2 font-medium",
                  row.dayPct === null
                    ? "text-muted-foreground"
                    : row.dayPct >= 0
                    ? "text-green-600"
                    : "text-red-600"
                )}
              >
                {row.dayPct !== null
                  ? `${row.dayPct >= 0 ? "+" : ""}${(row.dayPct * 100).toFixed(2)}%`
                  : "—"}
              </td>
              <td className="text-right py-2">
                <Sparkline5 values={row.sparkline} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </PanelShell>
  );
}
