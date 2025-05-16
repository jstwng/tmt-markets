import { useRef, useState, useCallback } from "react";
import { Button } from "@/components/ui/button";

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export default function ChatInput({ onSend, disabled, placeholder }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const resize = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    // Cap at 6 lines (~144px at 24px line-height)
    el.style.height = `${Math.min(el.scrollHeight, 144)}px`;
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    resize();
  };

  const handleSend = useCallback(() => {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue("");
    // Reset height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [value, disabled, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex items-end gap-2 bg-background border border-border rounded-xl px-3 py-2 focus-within:ring-1 focus-within:ring-ring transition-shadow">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder={placeholder ?? "Ask anything about your portfolio..."}
        rows={1}
        className="flex-1 resize-none bg-transparent text-sm leading-6 outline-none placeholder:text-muted-foreground disabled:opacity-50 min-h-[24px] max-h-[144px]"
      />
      <Button
        size="sm"
        onClick={handleSend}
        disabled={disabled || !value.trim()}
        className="shrink-0 h-8 px-3"
      >
        {disabled ? (
          <span className="inline-block w-3 h-3 border border-current rounded-full border-t-transparent animate-spin" />
        ) : (
          "Send"
        )}
      </Button>
    </div>
  );
}
