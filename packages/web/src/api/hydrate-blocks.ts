import type { ChartManifest } from "@/components/chat/charts/manifest/types";
import type { MessageBlock } from "./chat-types";

/**
 * Converts raw blocks loaded from the Supabase messages.blocks column into
 * display-ready MessageBlock[].
 *
 * New rows (written after the block_mapper.py fix) already contain correct
 * block types and pass through unchanged. Legacy rows may contain "tool_result"
 * blocks which are converted to their display equivalents here.
 *
 * Conversion rules:
 *   tool_result { name: "openbb_query", result.chart_manifest } → manifest_chart
 *   tool_result (any other)                                      → dropped
 *   all other block types                                        → pass through
 */
export function hydrateBlocks(raw: unknown[]): MessageBlock[] {
  const out: MessageBlock[] = [];

  for (const block of raw as Record<string, unknown>[]) {
    if (block.type === "tool_result") {
      const result = block.result as Record<string, unknown> | undefined;
      if (block.name === "openbb_query" && result?.chart_manifest) {
        out.push({
          type: "manifest_chart",
          manifest: result.chart_manifest as ChartManifest,
        });
      }
      // all other tool_result blocks dropped — no renderer exists
    } else {
      out.push(block as MessageBlock);
    }
  }

  return out;
}
