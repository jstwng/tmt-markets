import { useState } from "react";
import { supabase } from "@/lib/supabase";
import type { ChartManifest } from "./types";

interface SaveButtonProps {
  manifest: ChartManifest;
}

export default function SaveButton({ manifest }: SaveButtonProps) {
  const [status, setStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");

  async function handleSave() {
    if (status === "saving" || status === "saved") return;
    setStatus("saving");

    const { error } = await supabase.from("saved_outputs").insert({
      query: manifest.source.query,
      chart_manifest: manifest,
      openbb_call: manifest.source.openbb_call,
    });

    if (error) {
      console.error("Failed to save:", error);
      setStatus("error");
      setTimeout(() => setStatus("idle"), 3000);
    } else {
      setStatus("saved");
    }
  }

  return (
    <button
      onClick={handleSave}
      disabled={status === "saving" || status === "saved"}
      className="text-xs px-3 py-1.5 rounded-md border border-border text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
    >
      {status === "idle" && "Save"}
      {status === "saving" && "Saving..."}
      {status === "saved" && "✓ Saved"}
      {status === "error" && "Failed — retry?"}
    </button>
  );
}
