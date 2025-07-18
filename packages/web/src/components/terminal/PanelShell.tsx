import { cn } from "@/lib/utils";

interface PanelShellProps {
  title: string;
  lastUpdated: Date | null;
  error: string | null;
  loading: boolean;
  onRetry?: () => void;
  children: React.ReactNode;
  className?: string;
}

export default function PanelShell({
  title,
  lastUpdated,
  error,
  loading,
  onRetry,
  children,
  className,
}: PanelShellProps) {
  const updatedStr = lastUpdated
    ? lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : null;

  return (
    <div className={cn("border border-border rounded-lg overflow-hidden", className)}>
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {title}
        </span>
        {updatedStr && (
          <span className="text-xs text-muted-foreground/60">Updated {updatedStr}</span>
        )}
      </div>
      <div className="p-4">
        {error ? (
          <div className="flex items-center justify-between text-sm text-red-600">
            <span>Failed to load</span>
            {onRetry && (
              <button onClick={onRetry} className="text-xs underline ml-2">
                Retry
              </button>
            )}
          </div>
        ) : loading ? (
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-4 bg-muted/30 rounded animate-pulse" />
            ))}
          </div>
        ) : (
          children
        )}
      </div>
    </div>
  );
}
