import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { GroundingSource } from "@/api/chat-types";

interface CitationsFooterProps {
  sources: GroundingSource[];
}

export default function CitationsFooter({ sources }: CitationsFooterProps) {
  const [open, setOpen] = useState(false);

  if (sources.length === 0) return null;

  return (
    <div className="mt-2 border-t border-border pt-2">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors select-none"
      >
        {open ? (
          <ChevronDown className="w-3 h-3" />
        ) : (
          <ChevronRight className="w-3 h-3" />
        )}
        Sources ({sources.length})
      </button>

      {open && (
        <ol className="mt-2 space-y-1 list-none p-0">
          {sources.map((src) => (
            <li key={src.index} className="flex gap-1.5 text-[11px] text-muted-foreground leading-relaxed">
              <span className="shrink-0">{src.index}.</span>
              <span>
                <a
                  href={src.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 underline hover:text-blue-300"
                >
                  {src.title}
                </a>
                {src.date && (
                  <span className="ml-1.5 text-muted-foreground">· {src.date}</span>
                )}
              </span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
