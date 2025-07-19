import { useCallback, useRef, useState } from "react";
import type {
  ChatMessage,
  MessageBlock,
  ToolCallBlock,
} from "@/api/chat-types";
import { mapToolResultToBlocks } from "@/api/block-mapper";
import { hydrateBlocks } from "@/api/hydrate-blocks";
import { useAuth } from "@/contexts/AuthContext";
import { supabase } from "@/lib/supabase";

const API_BASE = "/api";

function generateId(): string {
  return Math.random().toString(36).slice(2, 11);
}

function toolDisplayName(name: string): string {
  const map: Record<string, string> = {
    fetch_prices: "Fetching price data",
    estimate_covariance: "Computing covariance matrix",
    optimize_portfolio: "Optimizing portfolio",
    run_backtest: "Running backtest",
    generate_efficient_frontier: "Generating efficient frontier",
    openbb_query: "Querying OpenBB market data",
    load_portfolio: "Loading portfolio",
    save_portfolio: "Saving portfolio",
    save_output: "Saving output",
  };
  return map[name] ?? name;
}

export interface UseChatReturn {
  messages: ChatMessage[];
  sendMessage: (text: string) => Promise<void>;
  loadConversation: (id: string) => Promise<void>;
  newConversation: () => void;
  isStreaming: boolean;
  conversationId: string | null;
  error: string | null;
}

export function useChat(initialConversationId?: string): UseChatReturn {
  const { session } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(
    initialConversationId ?? null
  );
  const [error, setError] = useState<string | null>(null);

  const toolStartTimes = useRef<Record<string, number>>({});

  const newConversation = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setError(null);
    toolStartTimes.current = {};
  }, []);

  // Load a past conversation from Supabase and restore messages from stored blocks
  const loadConversation = useCallback(
    async (id: string) => {
      setMessages([]);
      setConversationId(id);
      setError(null);
      toolStartTimes.current = {};

      const { data, error: fetchError } = await supabase
        .from("messages")
        .select("id, role, blocks, content, created_at")
        .eq("conversation_id", id)
        .order("created_at", { ascending: true });

      if (fetchError) {
        setError("Failed to load conversation history.");
        return;
      }

      console.debug(
        "[RELOAD_DEBUG] raw rows:",
        (data ?? []).map((r) => ({
          id: r.id,
          role: r.role,
          blocks_len: (r.blocks as unknown[] | null)?.length ?? null,
          blocks_types: (r.blocks as { type: string }[] | null)?.map((b) => b.type) ?? null,
        }))
      );

      const restored: ChatMessage[] = (data ?? []).map((row) => {
        const rawBlocks = (row.blocks as unknown[]) ?? [];
        const blocks =
          rawBlocks.length > 0
            ? hydrateBlocks(rawBlocks)
            : row.content
            ? [{ type: "text" as const, text: row.content as string }]
            : [];
        return {
          id: row.id,
          role: row.role as "user" | "assistant",
          blocks,
          timestamp: new Date(row.created_at).getTime(),
        };
      });

      console.debug(
        "[RELOAD_DEBUG] restored messages:",
        restored.map((m) => ({ id: m.id, role: m.role, blocks: m.blocks.map((b) => b.type) }))
      );

      setMessages(restored);
    },
    []
  );

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isStreaming) return;
      if (!session) {
        setError("Not authenticated.");
        return;
      }

      setError(null);

      const userMessage: ChatMessage = {
        id: generateId(),
        role: "user",
        blocks: [{ type: "text", text }],
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, userMessage]);

      const assistantId = generateId();
      setMessages((prev) => [
        ...prev,
        { id: assistantId, role: "assistant", blocks: [], timestamp: Date.now() },
      ]);

      setIsStreaming(true);

      const appendBlocks = (newBlocks: MessageBlock[]) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, blocks: [...m.blocks, ...newBlocks] }
              : m
          )
        );
      };

      const updateLastBlock = (
        updater: (block: MessageBlock) => MessageBlock,
        predicate: (block: MessageBlock) => boolean
      ) => {
        setMessages((prev) =>
          prev.map((m) => {
            if (m.id !== assistantId) return m;
            const blocks = [...m.blocks];
            for (let i = blocks.length - 1; i >= 0; i--) {
              if (predicate(blocks[i])) {
                blocks[i] = updater(blocks[i]);
                break;
              }
            }
            return { ...m, blocks };
          })
        );
      };

      const abortController = new AbortController();
      const timeoutId = window.setTimeout(() => abortController.abort(), 120_000);

      try {
        const response = await fetch(`${API_BASE}/agent/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${session.access_token}`,
          },
          body: JSON.stringify({
            message: text,
            conversation_id: conversationId,
          }),
          signal: abortController.signal,
        });

        if (!response.ok) {
          const detail = await response.text();
          throw new Error(`Server error ${response.status}: ${detail}`);
        }

        if (!response.body) throw new Error("No response body");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        let buffer = "";
        let currentEvent = "";
        let currentData = "";

        const dispatchEvent = (event: string, data: string) => {
          let parsed: Record<string, unknown>;
          try {
            parsed = JSON.parse(data);
          } catch {
            return;
          }

          switch (event) {
            case "conversation":
              setConversationId(parsed.conversation_id as string);
              break;

            case "tool_call": {
              const name = parsed.name as string;
              toolStartTimes.current[name] = Date.now();
              const toolBlock: ToolCallBlock = {
                type: "tool_call",
                name,
                displayName: toolDisplayName(name),
                args: (parsed.args ?? {}) as Record<string, unknown>,
                status: "pending",
              };
              appendBlocks([toolBlock]);
              break;
            }

            case "tool_result": {
              const name = parsed.name as string;
              const startTime = toolStartTimes.current[name];
              const durationMs = startTime ? Date.now() - startTime : undefined;

              updateLastBlock(
                (b) => ({ ...b, status: "complete" as const, durationMs }),
                (b) =>
                  b.type === "tool_call" &&
                  (b as ToolCallBlock).name === name &&
                  (b as ToolCallBlock).status === "pending"
              );

              const mapperInput = name === "openbb_query" ? parsed : parsed.result;
              const resultBlocks = mapToolResultToBlocks(name, mapperInput);
              if (resultBlocks.length > 0) appendBlocks(resultBlocks);
              break;
            }

            case "text": {
              const chunk = parsed.text as string;
              setMessages((prev) =>
                prev.map((m) => {
                  if (m.id !== assistantId) return m;
                  const blocks = m.blocks;
                  const last = blocks[blocks.length - 1];
                  if (last?.type === "text") {
                    return {
                      ...m,
                      blocks: [
                        ...blocks.slice(0, -1),
                        { ...last, text: last.text + chunk },
                      ],
                    };
                  }
                  return { ...m, blocks: [...blocks, { type: "text", text: chunk }] };
                })
              );
              break;
            }

            case "error": {
              const msg = parsed.message as string;
              appendBlocks([{ type: "error", message: msg }]);
              break;
            }

            case "codegen": {
              const attempt = parsed.attempt as number;
              const toolBlock: ToolCallBlock = {
                type: "tool_call",
                name: "openbb_query",
                displayName: `Generating OpenBB query (attempt ${attempt}/3)`,
                args: { code: parsed.code as string },
                status: "pending",
              };
              appendBlocks([toolBlock]);
              break;
            }

            case "codegen_retry": {
              const errMsg = parsed.error as string;
              const attempt = parsed.attempt as number;
              updateLastBlock(
                (b) => ({
                  ...b,
                  displayName: `Retrying OpenBB query (attempt ${attempt + 1}/3): ${errMsg}`,
                } as ToolCallBlock),
                (b) =>
                  b.type === "tool_call" &&
                  (b as ToolCallBlock).name === "openbb_query" &&
                  (b as ToolCallBlock).status === "pending"
              );
              break;
            }

            case "done":
              break;
          }
        };

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          let newlineIdx: number;
          while ((newlineIdx = buffer.indexOf("\n")) !== -1) {
            const raw = buffer.slice(0, newlineIdx);
            buffer = buffer.slice(newlineIdx + 1);
            const line = raw.replace(/\r$/, "");

            if (line.startsWith("event:")) {
              currentEvent = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              currentData = line.slice(5).trim();
            } else if (line === "" && currentEvent !== "") {
              dispatchEvent(currentEvent, currentData);
              currentEvent = "";
              currentData = "";
            }
          }
        }
      } catch (err) {
        const isAbort = err instanceof DOMException && err.name === "AbortError";
        const message = isAbort
          ? "Request timed out. Please try again."
          : err instanceof Error
          ? err.message
          : "Connection failed";
        setError(message);
        appendBlocks([{ type: "error", message }]);
      } finally {
        clearTimeout(timeoutId);
        setIsStreaming(false);
      }
    },
    [isStreaming, conversationId, session]
  );

  return {
    messages,
    sendMessage,
    loadConversation,
    newConversation,
    isStreaming,
    conversationId,
    error,
  };
}
