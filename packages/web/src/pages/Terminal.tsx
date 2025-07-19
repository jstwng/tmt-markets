import { useEffect, useRef, useState } from "react";
import MacroPanel from "@/components/terminal/MacroPanel";
import IndicesPanel from "@/components/terminal/IndicesPanel";
import MoversPanel from "@/components/terminal/MoversPanel";
import HeatmapPanel from "@/components/terminal/HeatmapPanel";
import CalendarPanel from "@/components/terminal/CalendarPanel";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const INTERVAL_OPTIONS = [
  { label: "1 min", ms: 60_000 },
  { label: "5 min", ms: 300_000 },
  { label: "15 min", ms: 900_000 },
  { label: "30 min", ms: 1_800_000 },
];

const STORAGE_KEY = "terminal_refresh_interval_ms";

function getStoredInterval(): number {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored) {
    const n = parseInt(stored, 10);
    if (INTERVAL_OPTIONS.some((o) => o.ms === n)) return n;
  }
  return 300_000;
}

export default function Terminal() {
  const [intervalMs, setIntervalMs] = useState<number>(getStoredInterval);
  const [countdown, setCountdown] = useState<number>(intervalMs / 1000);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    setCountdown(intervalMs / 1000);

    if (countdownRef.current) clearInterval(countdownRef.current);
    countdownRef.current = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) return intervalMs / 1000;
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (countdownRef.current) clearInterval(countdownRef.current);
    };
  }, [intervalMs]);

  function handleIntervalChange(value: string) {
    const ms = parseInt(value, 10);
    setIntervalMs(ms);
    localStorage.setItem(STORAGE_KEY, String(ms));
  }

  const mins = Math.floor(countdown / 60);
  const secs = countdown % 60;
  const countdownStr = `${mins}:${String(secs).padStart(2, "0")}`;

  return (
    <div className="py-6 space-y-3">
      <div className="flex items-center justify-between mb-1">
        <h1 className="text-base font-semibold tracking-tight">Market Overview</h1>
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground">Refresh</span>
          <Select value={String(intervalMs)} onValueChange={handleIntervalChange}>
            <SelectTrigger className="w-24 h-7 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {INTERVAL_OPTIONS.map((o) => (
                <SelectItem key={o.ms} value={String(o.ms)}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <span className="text-xs text-muted-foreground/60 tabular-nums">
            Next in {countdownStr}
          </span>
        </div>
      </div>

      <MacroPanel intervalMs={intervalMs} />

      <div className="grid grid-cols-2 gap-3">
        <IndicesPanel intervalMs={intervalMs} />
        <MoversPanel intervalMs={intervalMs} />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <HeatmapPanel intervalMs={intervalMs} />
        <CalendarPanel intervalMs={intervalMs} />
      </div>

      <div className="text-xs text-muted-foreground text-right">
        All data via OpenBB · Auto-refreshes every{" "}
        {INTERVAL_OPTIONS.find((o) => o.ms === intervalMs)?.label ?? "5 min"}
      </div>
    </div>
  );
}
