import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import ManifestChartBlock from "@/components/chat/ManifestChartBlock";
import type { ChartManifest } from "@/components/chat/charts/manifest/types";

interface SavedOutput {
  id: string;
  query: string;
  chart_manifest: ChartManifest;
  openbb_call: string;
  created_at: string;
}

export default function Saved() {
  const [outputs, setOutputs] = useState<SavedOutput[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const { data, error } = await supabase
        .from("saved_outputs")
        .select("*")
        .order("created_at", { ascending: false });

      if (!error && data) {
        setOutputs(data as SavedOutput[]);
      }
      setLoading(false);
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="py-20 text-center text-muted-foreground text-sm">
        Loading saved outputs...
      </div>
    );
  }

  if (outputs.length === 0) {
    return (
      <div className="py-20 text-center text-muted-foreground text-sm">
        No saved outputs yet. Save a chart from the chat to see it here.
      </div>
    );
  }

  return (
    <div className="py-6 space-y-4">
      <h1 className="text-lg font-semibold">Saved Outputs</h1>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {outputs.map((output) => (
          <div
            key={output.id}
            className="border border-border rounded-lg p-4 cursor-pointer hover:bg-muted/30 transition-colors"
            onClick={() => setExpanded(expanded === output.id ? null : output.id)}
          >
            <h3 className="text-sm font-medium truncate">
              {output.chart_manifest.title}
            </h3>
            <p className="text-xs text-muted-foreground mt-1 truncate">
              {output.query}
            </p>
            <p className="text-xs text-muted-foreground mt-2">
              {new Date(output.created_at).toLocaleDateString()}
            </p>
          </div>
        ))}
      </div>

      {expanded && (
        <div className="mt-6">
          <ManifestChartBlock
            manifest={outputs.find((o) => o.id === expanded)!.chart_manifest}
          />
        </div>
      )}
    </div>
  );
}
