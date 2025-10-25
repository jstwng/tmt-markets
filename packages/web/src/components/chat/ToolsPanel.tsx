import { useState, useEffect } from "react";
import { X, Search } from "lucide-react";
import { TOOLS_MANIFEST, CATEGORIES, type Tool } from "@/data/tools-manifest";

interface ToolsPanelProps {
  open: boolean;
  onClose: () => void;
}

export default function ToolsPanel({ open, onClose }: ToolsPanelProps) {
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!open) setQuery("");
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open]); // onClose intentionally omitted — handler captures latest value

  if (!open) return null;

  const q = query.trim().toLowerCase();
  const filtered = q
    ? TOOLS_MANIFEST.filter(
        (t) =>
          t.name.toLowerCase().includes(q) ||
          t.description.toLowerCase().includes(q)
      )
    : null;

  return (
    <>
      <div
        data-testid="tools-backdrop"
        className="fixed inset-0 z-40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Research tools"
        className="fixed top-0 right-0 z-50 h-screen w-72 bg-background border-l flex flex-col shadow-xl"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b shrink-0">
          <h2 className="text-sm font-semibold">Research Tools</h2>
          <button
            aria-label="Close"
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Search */}
        <div className="px-3 py-2 border-b shrink-0">
          <div className="flex items-center gap-2 bg-muted rounded-md px-3 py-1.5">
            <Search size={12} className="text-muted-foreground shrink-0" />
            <input
              type="text"
              placeholder="Search tools…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="bg-transparent text-xs outline-none flex-1 placeholder:text-muted-foreground"
            />
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto py-3">
          {filtered !== null ? (
            filtered.length === 0 ? (
              <p className="text-xs text-muted-foreground px-4 py-3">
                No tools match.
              </p>
            ) : (
              <div className="px-3 flex flex-col gap-2">
                {filtered.map((tool) => (
                  <ToolCard key={tool.name} tool={tool} />
                ))}
              </div>
            )
          ) : (
            CATEGORIES.map((category) => {
              const tools = TOOLS_MANIFEST.filter(
                (t) => t.category === category
              );
              return (
                <div key={category} className="mb-4">
                  <p className="px-4 pb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">
                    {category}
                  </p>
                  <div className="px-3 flex flex-col gap-2">
                    {tools.map((tool) => (
                      <ToolCard key={tool.name} tool={tool} />
                    ))}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </>
  );
}

function ToolCard({ tool }: { tool: Tool }) {
  return (
    <div className="rounded-md border bg-card px-3 py-2">
      <p className="text-xs font-medium text-foreground">{tool.name}</p>
      <p className="mt-1 text-[11px] text-muted-foreground/70 italic leading-relaxed">
        &ldquo;{tool.examplePrompt}&rdquo;
      </p>
    </div>
  );
}
