import { useTerminalPanel } from "@/hooks/useTerminalPanel";
import PanelShell from "./PanelShell";

const IMPORTANT_EVENTS = [
  "fomc", "cpi", "ppi", "nonfarm", "jobs", "unemployment", "gdp", "retail", "pce", "claims",
];

function extractEvents(
  rawData: unknown[]
): { date: string; event: string; consensus: string | null }[] {
  if (!Array.isArray(rawData) || rawData.length === 0) return [];
  return (rawData as Record<string, unknown>[])
    .filter((r) => {
      const name = String(r.event ?? r.name ?? r.description ?? "").toLowerCase();
      return IMPORTANT_EVENTS.some((k) => name.includes(k));
    })
    .sort((a, b) => String(a.date ?? "").localeCompare(String(b.date ?? "")))
    .slice(0, 8)
    .map((r) => ({
      date: r.date
        ? new Date(String(r.date)).toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
          })
        : "—",
      event: String(r.event ?? r.name ?? r.description ?? "Unknown"),
      consensus: r.consensus_estimate !== undefined
        ? String(r.consensus_estimate)
        : r.consensus !== undefined
        ? String(r.consensus)
        : r.estimate !== undefined
        ? String(r.estimate)
        : null,
    }));
}

export default function CalendarPanel({ intervalMs }: { intervalMs: number }) {
  const { data, loading, error, lastUpdated, refetch } = useTerminalPanel("calendar", intervalMs);
  const events = extractEvents(data?.raw_data ?? []);

  return (
    <PanelShell
      title="Macro Calendar"
      lastUpdated={lastUpdated}
      error={error}
      loading={loading}
      onRetry={refetch}
    >
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr className="border-b border-border">
            <th className="text-left py-1.5 font-medium text-muted-foreground">Date</th>
            <th className="text-left py-1.5 font-medium text-muted-foreground">Event</th>
            <th className="text-right py-1.5 font-medium text-muted-foreground">Consensus</th>
          </tr>
        </thead>
        <tbody>
          {events.length === 0 ? (
            <tr>
              <td colSpan={3} className="py-4 text-center text-muted-foreground">
                No upcoming events
              </td>
            </tr>
          ) : (
            events.map((ev, i) => (
              <tr key={i} className="border-b border-border/40 last:border-0">
                <td className="py-2 text-muted-foreground whitespace-nowrap pr-3">{ev.date}</td>
                <td className="py-2 font-medium">{ev.event}</td>
                <td className="py-2 text-right text-muted-foreground">{ev.consensus ?? "—"}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </PanelShell>
  );
}
