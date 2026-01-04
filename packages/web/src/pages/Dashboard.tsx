import { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { usePortfolioPerformance } from "@/hooks/usePortfolioPerformance";
import { createPortfolio, updatePortfolio, deletePortfolio } from "@/api/client";
import { computeTotal, computeWeights, scaleAmounts } from "@/lib/portfolio-math";
import type { DraftPosition } from "@/lib/portfolio-math";
import EquityCurve from "@/components/dashboard/EquityCurve";
import PositionsTable from "@/components/dashboard/PositionsTable";
import HoldingsPie from "@/components/dashboard/HoldingsPie";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

function usd(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);
}

function pct(n: number) {
  return `${n >= 0 ? "+" : ""}${(n * 100).toFixed(2)}%`;
}

function formatCurrency(n: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
}

const TOTAL_VALUE_KEY = (id: string) => `portfolio_total_value_${id}`;

type EditMode =
  | { type: "off" }
  | { type: "editing"; draft: { name: string; positions: DraftPosition[] } }
  | { type: "creating" }
  | { type: "deleting" };

export default function Dashboard() {
  const { session } = useAuth();
  const token = session?.access_token;

  const {
    portfolios,
    selectedId,
    setSelectedId,
    selectPortfolio,
    performance,
    slicedCurve,
    loading,
    error,
    period,
    setPeriod,
    refetchPortfolios,
    refetchPerformance,
  } = usePortfolioPerformance(token);

  const [totalValue, setTotalValue] = useState<number>(100_000);
  const [valueInput, setValueInput] = useState<string>("$100,000");
  const [editMode, setEditMode] = useState<EditMode>({ type: "off" });
  const [newPortfolioName, setNewPortfolioName] = useState("");
  const [saving, setSaving] = useState(false);

  // Load persisted total value when portfolio changes
  useEffect(() => {
    if (!selectedId) return;
    const stored = localStorage.getItem(TOTAL_VALUE_KEY(selectedId));
    const val = stored ? parseFloat(stored) : 100_000;
    setTotalValue(val);
    setValueInput(formatCurrency(val));
  }, [selectedId]);


  // --- Edit mode handlers ---

  function handleStartEdit() {
    if (!performance) return;
    const positions: DraftPosition[] = performance.positions.map((p) => ({
      ticker: p.ticker,
      amount: Math.round(p.weight * totalValue),
    }));
    setEditMode({ type: "editing", draft: { name: performance.portfolio_name, positions } });
  }

  function handleDraftChange(positions: DraftPosition[]) {
    if (editMode.type !== "editing") return;
    const newTotal = computeTotal(positions);
    setTotalValue(newTotal);
    setValueInput(formatCurrency(newTotal));
    setEditMode({ type: "editing", draft: { ...editMode.draft, positions } });
  }

  function handleEditTotalValue(raw: string) {
    if (editMode.type !== "editing") return;
    setValueInput(raw);
    const cleaned = raw.replace(/[^0-9.]/g, "");
    const newTotal = parseFloat(cleaned) || 0;
    if (newTotal > 0) {
      const scaled = scaleAmounts(editMode.draft.positions, newTotal);
      setEditMode({ type: "editing", draft: { ...editMode.draft, positions: scaled } });
      setTotalValue(newTotal);
    }
  }

  function handleEditTotalBlur() {
    const cleaned = valueInput.replace(/[^0-9.]/g, "");
    const newTotal = parseFloat(cleaned) || 0;
    if (editMode.type === "editing") {
      if (newTotal > 0) {
        setValueInput(formatCurrency(newTotal));
      } else {
        // restore current totalValue display if user cleared to zero
        setValueInput(formatCurrency(totalValue));
      }
    }
  }

  function handleCancelEdit() {
    setEditMode({ type: "off" });
    if (selectedId) {
      const stored = localStorage.getItem(TOTAL_VALUE_KEY(selectedId));
      const val = stored ? parseFloat(stored) : 100_000;
      setTotalValue(val);
      setValueInput(formatCurrency(val));
    }
  }

  async function handleSave() {
    if (editMode.type !== "editing" || !token || !selectedId) return;
    const { name, positions } = editMode.draft;
    const weights = computeWeights(positions);
    const tickers = positions.map((p) => p.ticker.toUpperCase());
    setSaving(true);
    try {
      await updatePortfolio(token, selectedId, { name, tickers, weights });
      localStorage.setItem(TOTAL_VALUE_KEY(selectedId), String(computeTotal(positions)));
      refetchPortfolios();
      refetchPerformance();
      setEditMode({ type: "off" });
    } catch (e) {
      // keep edit mode open so user can retry
    } finally {
      setSaving(false);
    }
  }

  // --- Create portfolio ---

  function handleStartCreate() {
    setNewPortfolioName("");
    setEditMode({ type: "creating" });
  }

  async function handleConfirmCreate() {
    if (!token || !newPortfolioName.trim()) return;
    setSaving(true);
    try {
      const created = await createPortfolio(token, {
        name: newPortfolioName.trim(),
        tickers: [],
        weights: [],
      });
      refetchPortfolios();
      setSelectedId(created.id);
      setEditMode({
        type: "editing",
        draft: { name: created.name, positions: [] },
      });
      setTotalValue(0);
      setValueInput("$0");
    } catch (e) {
      // stay on create prompt so user can retry
    } finally {
      setSaving(false);
    }
  }

  // --- Delete portfolio ---

  function handleStartDelete() {
    setEditMode({ type: "deleting" });
  }

  async function handleConfirmDelete() {
    if (!token || !selectedId) return;
    setSaving(true);
    try {
      await deletePortfolio(token, selectedId);
      refetchPortfolios();
      setEditMode({ type: "off" });
    } catch (e) {
      setEditMode({ type: "off" });
    } finally {
      setSaving(false);
    }
  }

  const todayChange = performance
    ? performance.positions.reduce((acc, p) => acc + p.day_pct * p.weight, 0)
    : 0;
  const todayChangeDollar = todayChange * totalValue;
  const lastUpdated = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const isEditing = editMode.type === "editing";
  const draft = editMode.type === "editing" ? editMode.draft : null;
  const selectedPortfolio = portfolios.find((p) => p.id === selectedId);
  const selectedName = portfolios.find((p) => p.id === selectedId)?.name;

  return (
    <div className="py-6 space-y-4 max-w-4xl">
      {/* Selector bar */}
      <div className="flex items-center justify-between gap-3">
        {/* Left: portfolio selector or edit name */}
        <div className="flex items-center gap-3 min-w-0">
          {isEditing && draft ? (
            <input
              className="w-48 h-8 text-sm border border-border rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-foreground bg-background"
              value={draft.name}
              onChange={(e) =>
                setEditMode({ type: "editing", draft: { ...draft, name: e.target.value } })
              }
              aria-label="Portfolio name"
            />
          ) : (
            <>
              <span className="text-xs text-muted-foreground uppercase tracking-wide shrink-0">
                Portfolio
              </span>
              {(() => {
                const selectedName = portfolios.find((p) => p.id === selectedId)?.name;
                return (
                  <Select
                    value={selectedId}
                    onValueChange={selectPortfolio}
                    disabled={portfolios.length === 0 || editMode.type !== "off"}
                  >
                    <SelectTrigger className="w-48 h-8 text-sm">
                      <SelectValue placeholder={loading ? "Loading..." : "No portfolios"}>
                        {selectedName}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      {portfolios.map((p) => (
                        <SelectItem key={p.id} value={p.id}>
                          {p.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                );
              })()}
            </>
          )}
        </div>

        {/* Right: action buttons */}
        <div className="flex items-center gap-2 shrink-0">
          {editMode.type === "off" && (
            <>
              {selectedId && performance && (
                <button
                  onClick={handleStartEdit}
                  className="text-xs text-muted-foreground hover:text-foreground border border-border rounded px-2 py-1 transition-colors"
                >
                  Edit
                </button>
              )}
              <button
                onClick={handleStartCreate}
                className="text-xs text-muted-foreground hover:text-foreground border border-border rounded px-2 py-1 transition-colors"
              >
                + New
              </button>
              {selectedId && portfolios.length > 0 && (
                <button
                  onClick={handleStartDelete}
                  className="text-xs text-muted-foreground hover:text-destructive border border-border rounded px-2 py-1 transition-colors"
                >
                  Delete
                </button>
              )}
            </>
          )}

          {isEditing && (
            <>
              <button
                onClick={handleSave}
                disabled={saving}
                className="text-xs border border-border rounded px-2 py-1 text-foreground hover:bg-accent transition-colors disabled:opacity-50"
              >
                {saving ? "Saving…" : "Save"}
              </button>
              <button
                onClick={handleCancelEdit}
                className="text-xs text-muted-foreground hover:text-foreground border border-border rounded px-2 py-1 transition-colors"
              >
                Cancel
              </button>
            </>
          )}
        </div>
      </div>

      {/* Inline: New portfolio name prompt */}
      {editMode.type === "creating" && (
        <div className="border border-border rounded-lg px-4 py-3 flex items-center gap-3">
          <span className="text-xs text-muted-foreground uppercase tracking-wide shrink-0">
            Portfolio name
          </span>
          <input
            autoFocus
            className="flex-1 text-sm border-b border-border bg-transparent focus:outline-none focus:border-foreground"
            placeholder="e.g. Growth Portfolio"
            value={newPortfolioName}
            onChange={(e) => setNewPortfolioName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleConfirmCreate();
              if (e.key === "Escape") setEditMode({ type: "off" });
            }}
          />
          <button
            onClick={handleConfirmCreate}
            disabled={!newPortfolioName.trim() || saving}
            className="text-xs border border-border rounded px-3 py-1 text-foreground hover:bg-accent transition-colors disabled:opacity-40"
          >
            {saving ? "Creating…" : "Create →"}
          </button>
          <button
            onClick={() => setEditMode({ type: "off" })}
            className="text-xs text-muted-foreground hover:text-foreground"
            aria-label="Cancel create"
          >
            ✕
          </button>
        </div>
      )}

      {/* Inline: Delete confirmation */}
      {editMode.type === "deleting" && (
        <div className="border border-destructive/30 rounded-lg px-4 py-3 flex items-center gap-3">
          <span className="text-sm text-muted-foreground flex-1">
            Delete{" "}
            <span className="font-semibold text-foreground">
              {selectedPortfolio?.name ?? "this portfolio"}
            </span>
            ? This cannot be undone.
          </span>
          <button
            onClick={handleConfirmDelete}
            disabled={saving}
            className="text-xs text-destructive border border-destructive/50 rounded px-3 py-1 hover:bg-destructive/10 transition-colors disabled:opacity-50"
          >
            {saving ? "Deleting…" : "Confirm"}
          </button>
          <button
            onClick={() => setEditMode({ type: "off" })}
            className="text-xs text-muted-foreground hover:text-foreground border border-border rounded px-2 py-1 transition-colors"
          >
            Cancel
          </button>
        </div>
      )}

      {error && (
        <div className="text-sm text-red-600 border border-red-200 bg-red-50 rounded px-3 py-2">
          {error}
        </div>
      )}

      {/* Empty state — no portfolios */}
      {!loading && portfolios.length === 0 && editMode.type === "off" && (
        <div className="text-center py-16 text-muted-foreground">
          <div className="text-sm mb-3">No portfolios yet.</div>
          <button
            onClick={handleStartCreate}
            className="text-sm border border-border rounded px-4 py-2 hover:bg-accent transition-colors"
          >
            + Create your first portfolio
          </button>
        </div>
      )}

      {/* Dashboard content */}
      {(selectedId || isEditing) && (
        <>
          {/* Big portfolio value */}
          <div className="text-center py-2">
            <div className="text-4xl font-bold tracking-tight">
              {isEditing ? (
                <input
                  className="text-4xl font-bold tracking-tight text-center w-48 bg-transparent border-b border-border focus:outline-none focus:border-foreground"
                  value={valueInput}
                  onChange={(e) => handleEditTotalValue(e.target.value)}
                  onBlur={handleEditTotalBlur}
                  onKeyDown={(e) => e.key === "Enter" && handleEditTotalBlur()}
                  aria-label="Total portfolio value"
                />
              ) : (
                usd(totalValue)
              )}
            </div>
            {!isEditing && (
              <div
                className={cn(
                  "text-sm mt-1 font-medium",
                  todayChange >= 0 ? "text-green-600" : "text-red-600"
                )}
              >
                {todayChange >= 0 ? "+" : ""}
                {usd(todayChangeDollar)} ({pct(todayChange)}) Today
              </div>
            )}
            {isEditing && (
              <div className="text-xs text-muted-foreground mt-1">
                Edit to scale all positions proportionally
              </div>
            )}
          </div>

          {/* Equity curve — hidden in edit mode */}
          {!isEditing && (
            <EquityCurve
              curve={slicedCurve}
              period={period}
              onPeriodChange={setPeriod}
              loading={loading}
            />
          )}

          {/* Pie + stats — hidden in edit mode */}
          {!isEditing && (
            <div className="grid grid-cols-2 gap-4">
              <HoldingsPie positions={performance?.positions ?? []} loading={loading} />
              <div className="grid grid-cols-2 gap-3">
                {(() => {
                  const inceptionYear = performance?.curve[0]?.date?.slice(0, 4);
                  const sinceLabel = inceptionYear ? `since ${inceptionYear}` : "full history";
                  return [
                    {
                      label: "Total Return",
                      sublabel: sinceLabel,
                      value: performance ? pct(performance.stats.total_return) : "—",
                      positive: (performance?.stats.total_return ?? 0) >= 0,
                    },
                    {
                      label: "vs SPY",
                      sublabel: sinceLabel,
                      value: performance ? pct(performance.stats.alpha) : "—",
                      positive: (performance?.stats.alpha ?? 0) >= 0,
                    },
                    {
                      label: "Sharpe Ratio",
                      sublabel: "annualized",
                      value: performance ? performance.stats.sharpe.toFixed(2) : "—",
                      positive: null,
                    },
                    {
                      label: "Max Drawdown",
                      sublabel: sinceLabel,
                      value: performance ? pct(performance.stats.max_drawdown) : "—",
                      positive: (performance?.stats.max_drawdown ?? -1) >= 0,
                    },
                  ];
                })().map((stat) => (
                  <div key={stat.label} className="border border-border rounded-lg p-3">
                    <div className="text-xs text-muted-foreground">{stat.label}</div>
                    <div
                      className={cn(
                        "text-lg font-bold mt-1",
                        stat.positive === null
                          ? ""
                          : stat.positive
                          ? "text-green-600"
                          : "text-red-600"
                      )}
                    >
                      {loading ? (
                        <div className="h-5 w-16 bg-muted/40 rounded animate-pulse" />
                      ) : (
                        stat.value
                      )}
                    </div>
                    <div className="text-[10px] text-muted-foreground/60 mt-0.5">
                      {loading ? null : stat.sublabel}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Positions table */}
          <PositionsTable
            positions={performance?.positions ?? []}
            totalValue={totalValue}
            loading={loading && !isEditing}
            isEditMode={isEditing}
            draft={draft?.positions ?? []}
            onDraftChange={handleDraftChange}
          />

          <div className="text-xs text-muted-foreground text-right">
            Prices via yfinance · Last updated {lastUpdated}
          </div>
        </>
      )}
    </div>
  );
}
