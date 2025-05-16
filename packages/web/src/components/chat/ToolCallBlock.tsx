import { useState } from "react";
import type { ToolCallBlock as ToolCallBlockType } from "@/api/chat-types";

interface ToolCallBlockProps {
  block: ToolCallBlockType;
}

export default function ToolCallBlock({ block }: ToolCallBlockProps) {
  const [expanded, setExpanded] = useState(false);

  const isPending = block.status === "pending";
  const duration =
    block.durationMs !== undefined
      ? `${(block.durationMs / 1000).toFixed(1)}s`
      : null;

  return (
    <div className="flex flex-col gap-0.5">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors text-left"
      >
        {/* Status indicator */}
        {isPending ? (
          <span className="inline-block w-3 h-3 border border-muted-foreground/50 rounded-full border-t-foreground animate-spin" />
        ) : (
          <span className="inline-block w-3 h-3 rounded-full bg-foreground/20 flex items-center justify-center text-[8px]">
            ✓
          </span>
        )}
        <span className="font-medium">{block.displayName}</span>
        {duration && <span className="text-muted-foreground/70">· {duration}</span>}
        <span className="ml-auto">{expanded ? "▲" : "▼"}</span>
      </button>

      {expanded && (
        <pre className="mt-1 ml-5 text-xs bg-muted rounded px-3 py-2 overflow-x-auto font-mono leading-relaxed">
          {JSON.stringify(block.args, null, 2)}
        </pre>
      )}
    </div>
  );
}
