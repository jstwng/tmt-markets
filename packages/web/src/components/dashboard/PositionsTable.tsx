import type { PositionData } from "@/api/client";
import type { DraftPosition } from "@/lib/portfolio-math";
import { computeWeights } from "@/lib/portfolio-math";
import { cn } from "@/lib/utils";

interface PositionsTableProps {
  positions: PositionData[];
  totalValue: number;
  loading?: boolean;
  isEditMode?: boolean;
  draft?: DraftPosition[];
  onDraftChange?: (draft: DraftPosition[]) => void;
}

function pct(n: number) {
  return `${n >= 0 ? "+" : ""}${(n * 100).toFixed(2)}%`;
}

function usd(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);
}

export default function PositionsTable({
  positions,
  totalValue,
  loading,
  isEditMode = false,
  draft = [],
  onDraftChange,
}: PositionsTableProps) {
  const weights = computeWeights(draft);

  function handleTickerChange(index: number, value: string) {
    const next = draft.map((p, i) => (i === index ? { ...p, ticker: value.toUpperCase() } : p));
    onDraftChange?.(next);
  }

  function handleAmountChange(index: number, raw: string) {
    const cleaned = raw.replace(/[^0-9.]/g, "");
    // Don't parse if still mid-entry (trailing dot)
    if (cleaned.endsWith(".")) return;
    const amount = parseFloat(cleaned) || 0;
    const next = draft.map((p, i) => (i === index ? { ...p, amount } : p));
    onDraftChange?.(next);
  }

  function handleDeleteRow(index: number) {
    onDraftChange?.(draft.filter((_, i) => i !== index));
  }

  function handleAddRow() {
    onDraftChange?.([...draft, { ticker: "", amount: 0 }]);
  }

  if (isEditMode) {
    return (
      <div className="border border-border rounded-lg overflow-hidden">
        <div className="px-4 py-2.5 border-b border-border">
          <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Positions
          </span>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left px-4 py-2 text-xs font-medium text-muted-foreground">Ticker</th>
              <th className="text-right px-4 py-2 text-xs font-medium text-muted-foreground">Weight</th>
              <th className="text-right px-4 py-2 text-xs font-medium text-muted-foreground">Amount</th>
              <th className="w-8" />
            </tr>
          </thead>
          <tbody>
            {draft.map((pos, i) => (
              <tr key={i} className="border-b border-border/50 last:border-0">
                <td className="px-4 py-2">
                  <input
                    className="w-24 bg-transparent border-b border-border focus:border-foreground outline-none text-sm font-semibold"
                    value={pos.ticker}
                    onChange={(e) => handleTickerChange(i, e.target.value)}
                    placeholder="TICKER"
                  />
                </td>
                <td className="px-4 py-2 text-right text-muted-foreground text-sm">
                  {weights[i] !== undefined ? `${(weights[i] * 100).toFixed(1)}%` : "—"}
                </td>
                <td className="px-4 py-2 text-right">
                  <input
                    className="w-28 text-right bg-transparent border-b border-border focus:border-foreground outline-none text-sm"
                    value={pos.amount === 0 ? "" : String(pos.amount)}
                    onChange={(e) => handleAmountChange(i, e.target.value)}
                    placeholder="$0"
                  />
                </td>
                <td className="px-4 py-2 text-center">
                  <button
                    onClick={() => handleDeleteRow(i)}
                    className="text-muted-foreground hover:text-destructive transition-colors text-base leading-none"
                    aria-label={`Remove ${pos.ticker || "position"}`}
                  >
                    ×
                  </button>
                </td>
              </tr>
            ))}
            <tr>
              <td colSpan={4} className="px-4 py-2 border-t border-dashed border-border/50">
                <button
                  onClick={handleAddRow}
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  + Add position
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <div className="px-4 py-2.5 border-b border-border">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Positions
        </span>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border">
            <th className="text-left px-4 py-2 text-xs font-medium text-muted-foreground">Ticker</th>
            <th className="text-right px-4 py-2 text-xs font-medium text-muted-foreground">Weight</th>
            <th className="text-right px-4 py-2 text-xs font-medium text-muted-foreground">Price</th>
            <th className="text-right px-4 py-2 text-xs font-medium text-muted-foreground">Day</th>
            <th className="text-right px-4 py-2 text-xs font-medium text-muted-foreground">Value</th>
            <th className="text-right px-4 py-2 text-xs font-medium text-muted-foreground">Return</th>
          </tr>
        </thead>
        <tbody>
          {loading
            ? Array.from({ length: 4 }).map((_, i) => (
                <tr key={i} className="border-b border-border/50">
                  {Array.from({ length: 6 }).map((_, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-4 bg-muted/40 rounded animate-pulse" />
                    </td>
                  ))}
                </tr>
              ))
            : positions.map((pos) => (
                <tr key={pos.ticker} className="border-b border-border/50 last:border-0">
                  <td className="px-4 py-3 font-semibold">{pos.ticker}</td>
                  <td className="px-4 py-3 text-right text-muted-foreground">
                    {(pos.weight * 100).toFixed(1)}%
                  </td>
                  <td className="px-4 py-3 text-right">{usd(pos.price)}</td>
                  <td
                    className={cn(
                      "px-4 py-3 text-right font-medium",
                      pos.day_pct >= 0 ? "text-green-600" : "text-red-600"
                    )}
                  >
                    {pct(pos.day_pct)}
                  </td>
                  <td className="px-4 py-3 text-right font-medium">
                    {usd(pos.weight * totalValue)}
                  </td>
                  <td
                    className={cn(
                      "px-4 py-3 text-right font-medium",
                      pos.total_return >= 0 ? "text-green-600" : "text-red-600"
                    )}
                  >
                    {pct(pos.total_return)}
                  </td>
                </tr>
              ))}
        </tbody>
      </table>
    </div>
  );
}
