import type { MetricsBlock as MetricsBlockType } from "@/api/chat-types";

interface MetricsBlockProps {
  block: MetricsBlockType;
}

export default function MetricsBlock({ block }: MetricsBlockProps) {
  if (block.items.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-x-6 gap-y-2 py-2 border-b border-border/50">
      {block.items.map((item) => (
        <div key={item.label} className="flex flex-col">
          <span className="text-xs text-muted-foreground uppercase tracking-wide leading-none mb-1">
            {item.label}
          </span>
          <span className="text-sm font-medium tabular-nums">{item.value}</span>
        </div>
      ))}
    </div>
  );
}
