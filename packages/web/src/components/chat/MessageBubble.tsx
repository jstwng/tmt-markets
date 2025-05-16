import type { ChatMessage } from "@/api/chat-types";
import TextBlock from "./TextBlock";
import ChartBlock from "./ChartBlock";
import MetricsBlock from "./MetricsBlock";
import TableBlock from "./TableBlock";
import ToolCallBlock from "./ToolCallBlock";
import StreamingIndicator from "./StreamingIndicator";

interface MessageBubbleProps {
  message: ChatMessage;
  isStreaming?: boolean;
}

export default function MessageBubble({ message, isStreaming }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isEmpty = message.blocks.length === 0;

  if (isUser) {
    const textBlock = message.blocks.find((b) => b.type === "text");
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] bg-muted rounded-2xl px-4 py-2.5 text-sm">
          {textBlock?.type === "text" ? textBlock.text : ""}
        </div>
      </div>
    );
  }

  // Assistant message
  return (
    <div className="flex justify-start">
      <div className="max-w-[90%] w-full space-y-3">
        {isEmpty && isStreaming && <StreamingIndicator />}

        {message.blocks.map((block, i) => {
          switch (block.type) {
            case "text":
              return <TextBlock key={i} text={block.text} />;

            case "chart":
              return (
                <div key={i} className="rounded border border-border overflow-hidden">
                  <ChartBlock block={block} />
                </div>
              );

            case "metrics":
              return <MetricsBlock key={i} block={block} />;

            case "table":
              return <TableBlock key={i} block={block} />;

            case "tool_call":
              return <ToolCallBlock key={i} block={block} />;

            case "error":
              return (
                <div
                  key={i}
                  className="text-sm text-destructive bg-destructive/10 rounded px-3 py-2"
                >
                  {block.message}
                </div>
              );

            default:
              return null;
          }
        })}

        {!isEmpty && isStreaming && (
          <StreamingIndicator />
        )}
      </div>
    </div>
  );
}
