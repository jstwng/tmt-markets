import { mapToolResultToBlocks } from "./block-mapper";
import type { MessageBlock } from "./chat-types";

/**
 * Converts raw blocks loaded from the Supabase messages.blocks column into
 * display-ready MessageBlock[].
 *
 * New rows (written after the block_mapper.py fix) contain correct block types
 * and pass through unchanged (manifest_chart, text, tool_call, etc.).
 * Legacy rows contain "tool_result" blocks which are converted here using the
 * same mapToolResultToBlocks function that the live SSE path uses — guaranteeing
 * identical rendering on reload vs. live.
 *
 * Conversion rules:
 *   tool_result → mapToolResultToBlocks(name, result) → display blocks
 *   all other block types                             → pass through
 */
export function hydrateBlocks(raw: unknown[]): MessageBlock[] {
  const out: MessageBlock[] = [];

  for (const block of raw as Record<string, unknown>[]) {
    if (block.type === "tool_result") {
      const converted = mapToolResultToBlocks(
        block.name as string,
        block.result
      );
      out.push(...converted);
    } else {
      out.push(block as unknown as MessageBlock);
    }
  }

  return out;
}
