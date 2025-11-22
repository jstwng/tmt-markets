import { useTerminalPanel } from "@/hooks/useTerminalPanel";
import PanelShell from "./PanelShell";

function extractMovers(rawData: unknown[]): {
  gainers: { ticker: string; pct: number }[];
  losers: { ticker: string; pct: number }[];
} {
  if (!Array.isArray(rawData) || rawData.length === 0) {
    return { gainers: [], losers: [] };
  }
  const withPct = (rawData as Record<string, unknown>[])
    .map((r) => ({
      ticker: String(r.symbol ?? r.ticker ?? ""),
      pct: parseFloat(
        String(r.pct_change ?? r.percent_change ?? r.change_percent ?? r.day_change_percent ?? 0)
      ),
    }))
    .filter((r) => r.ticker && isFinite(r.pct))
    .sort((a, b) => b.pct - a.pct);

  return {
    gainers: withPct.slice(0, 5),
    losers: withPct.slice(-5).reverse(),
  };
}

export default function MoversPanel({ intervalMs }: { intervalMs: number }) {
  const { data, loading, error, lastUpdated, refetch } = useTerminalPanel("movers", intervalMs);
  const { gainers, losers } = extractMovers(data?.raw_data ?? []);

  return (
    <PanelShell
      title="Top Movers — S&P 500"
      lastUpdated={lastUpdated}
      error={error}
      loading={loading}
      onRetry={refetch}
    >
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="text-xs font-semibold text-green-600 uppercase tracking-wide mb-2">
            Gainers
          </div>
          <table className="w-full text-xs border-collapse">
            <tbody>
              {gainers.length === 0
                ? Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i}>
                      <td className="py-1.5">
                        <div className="h-3 bg-muted/30 rounded animate-pulse" />
                      </td>
                    </tr>
                  ))
                : gainers.map((g) => (
                    <tr key={g.ticker} className="border-b border-border/30 last:border-0">
                      <td className="py-1.5 font-semibold">{g.ticker}</td>
                      <td className="py-1.5 text-right text-green-600 font-medium">
                        +{g.pct.toFixed(2)}%
                      </td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>
        <div>
          <div className="text-xs font-semibold text-red-600 uppercase tracking-wide mb-2">
            Losers
          </div>
          <table className="w-full text-xs border-collapse">
            <tbody>
              {losers.length === 0
                ? Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i}>
                      <td className="py-1.5">
                        <div className="h-3 bg-muted/30 rounded animate-pulse" />
                      </td>
                    </tr>
                  ))
                : losers.map((l) => (
                    <tr key={l.ticker} className="border-b border-border/30 last:border-0">
                      <td className="py-1.5 font-semibold">{l.ticker}</td>
                      <td className="py-1.5 text-right text-red-600 font-medium">
                        {l.pct.toFixed(2)}%
                      </td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>
      </div>
    </PanelShell>
  );
}
