import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router";
import { Wrench } from "lucide-react";
import { useChat } from "@/hooks/useChat";
import { useConversations } from "@/hooks/useConversations";
import MessageBubble from "@/components/chat/MessageBubble";
import ChatInput from "@/components/chat/ChatInput";
import Sidebar from "@/components/chat/Sidebar";
import ToolsPanel from "@/components/chat/ToolsPanel";
import { Button } from "@/components/ui/button";

const SUGGESTED_PROMPTS = [
  "Optimize a portfolio of AAPL, MSFT, GOOGL, and AMZN over the last 2 years",
  "Show the efficient frontier for SPY, TLT, GLD, and QQQ",
  "Backtest a 60/40 SPY/TLT portfolio from 2022 to 2024",
  "What is the covariance matrix for the Mag 7 stocks in 2024?",
];

export default function Chat() {
  const { conversationId: urlConversationId } = useParams<{
    conversationId: string;
  }>();
  const navigate = useNavigate();

  const {
    messages,
    sendMessage,
    loadConversation,
    newConversation,
    isStreaming,
    conversationId,
  } = useChat();

  const { refetch } = useConversations();
  const bottomRef = useRef<HTMLDivElement>(null);
  const loadedRef = useRef<string | null>(null);

  // Load conversation from URL param on mount or when URL changes
  useEffect(() => {
    if (urlConversationId && urlConversationId !== loadedRef.current) {
      loadedRef.current = urlConversationId;
      loadConversation(urlConversationId);
    } else if (!urlConversationId && loadedRef.current !== null) {
      loadedRef.current = null;
      newConversation();
    }
  }, [urlConversationId, loadConversation, newConversation]);

  // Sync conversationId back to URL after first message creates it
  useEffect(() => {
    if (conversationId && !urlConversationId) {
      navigate(`/c/${conversationId}`, { replace: true });
      refetch();
    }
  }, [conversationId, urlConversationId, navigate, refetch]);

  // Auto-scroll to bottom when messages update
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleNewConversation = () => {
    newConversation();
    loadedRef.current = null;
  };

  const isEmpty = messages.length === 0;

  const [toolsPanelOpen, setToolsPanelOpen] = useState(false);

  return (
    <>
      <div className="flex h-[calc(100vh-3.5rem)]">
        {/* Sidebar */}
        <Sidebar
          activeConversationId={conversationId}
          onNewConversation={handleNewConversation}
        />

        {/* Main chat area */}
        <div className="flex flex-col flex-1 min-w-0">
          {/* Header strip */}
          <div className="flex items-center justify-between py-3 border-b shrink-0 px-6">
            <div>
              <h1 className="text-base font-semibold tracking-tight">
                Research Assistant
              </h1>
              <p className="text-xs text-muted-foreground">
                Ask questions in natural language — portfolio analysis, backtesting,
                and more
              </p>
            </div>
            {!isEmpty && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  handleNewConversation();
                  navigate("/");
                }}
                className="text-xs"
              >
                New conversation
              </Button>
            )}
          </div>

          {/* Message area */}
          <div className="flex-1 overflow-y-auto py-6">
            <div className="max-w-2xl mx-auto px-4 space-y-6">
              {isEmpty ? (
                <EmptyState onPrompt={sendMessage} />
              ) : (
                messages.map((message) => (
                  <MessageBubble
                    key={message.id}
                    message={message}
                    isStreaming={
                      isStreaming && message === messages[messages.length - 1]
                    }
                  />
                ))
              )}
              <div ref={bottomRef} />
            </div>
          </div>

          {/* Input bar */}
          <div className="shrink-0 border-t py-3">
            <div className="max-w-2xl mx-auto px-4">
              <ChatInput onSend={sendMessage} disabled={isStreaming} />
              <p className="text-[11px] text-muted-foreground/60 mt-2 text-center">
                Enter to send · Shift+Enter for new line
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Tools panel */}
      <ToolsPanel
        open={toolsPanelOpen}
        onClose={() => setToolsPanelOpen(false)}
      />

      {/* FAB */}
      <button
        onClick={() => setToolsPanelOpen((v) => !v)}
        aria-label="Open research tools"
        className="fixed bottom-6 right-6 z-30 flex h-10 w-10 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg hover:bg-primary/90 transition-colors"
      >
        <Wrench size={18} />
      </button>
    </>
  );
}

function EmptyState({ onPrompt }: { onPrompt: (text: string) => void }) {
  return (
    <div className="flex flex-col items-center gap-8 pt-12">
      <div className="text-center">
        <h2 className="text-2xl font-semibold tracking-tight">TMT Markets</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Quantitative investment research, powered by AI
        </p>
      </div>

      <div className="w-full grid grid-cols-1 gap-2 sm:grid-cols-2">
        {SUGGESTED_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            onClick={() => onPrompt(prompt)}
            className="text-left text-sm px-4 py-3 rounded-xl border border-border hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}
