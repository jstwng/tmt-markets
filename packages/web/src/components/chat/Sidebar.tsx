import { useState, useRef, useEffect } from "react";
import { Link, useNavigate } from "react-router";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useConversations } from "@/hooks/useConversations";
import type { Conversation } from "@/hooks/useConversations";

interface SidebarProps {
  activeConversationId: string | null;
  onNewConversation: () => void;
}

export default function Sidebar({
  activeConversationId,
  onNewConversation,
}: SidebarProps) {
  const { groups, loading, renameConversation, deleteConversation } =
    useConversations();
  const navigate = useNavigate();

  const handleDelete = async (id: string) => {
    await deleteConversation(id);
    if (activeConversationId === id) {
      navigate("/");
      onNewConversation();
    }
  };

  if (loading) {
    return (
      <aside className="w-56 shrink-0 border-r flex flex-col h-full">
        <div className="p-3 border-b">
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start text-xs"
            onClick={onNewConversation}
          >
            + New conversation
          </Button>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <p className="text-xs text-muted-foreground">Loading...</p>
        </div>
      </aside>
    );
  }

  return (
    <aside className="w-56 shrink-0 border-r flex flex-col h-full overflow-hidden">
      <div className="p-3 border-b shrink-0">
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start text-xs"
          onClick={() => {
            onNewConversation();
            navigate("/");
          }}
        >
          + New conversation
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto py-2">
        {groups.length === 0 ? (
          <p className="text-xs text-muted-foreground px-3 py-4">
            No conversations yet
          </p>
        ) : (
          groups.map((group) => (
            <div key={group.label} className="mb-2">
              <p className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">
                {group.label}
              </p>
              {group.items.map((conv) => (
                <ConversationItem
                  key={conv.id}
                  conversation={conv}
                  isActive={conv.id === activeConversationId}
                  onRename={renameConversation}
                  onDelete={handleDelete}
                />
              ))}
            </div>
          ))
        )}
      </div>
    </aside>
  );
}

interface ConversationItemProps {
  conversation: Conversation;
  isActive: boolean;
  onRename: (id: string, title: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}

function ConversationItem({
  conversation,
  isActive,
  onRename,
  onDelete,
}: ConversationItemProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(
    conversation.title ?? "Untitled conversation"
  );
  const [showMenu, setShowMenu] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isEditing) inputRef.current?.select();
  }, [isEditing]);

  // Close menu on outside click
  useEffect(() => {
    if (!showMenu) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowMenu(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showMenu]);

  const commitRename = async () => {
    setIsEditing(false);
    const trimmed = editValue.trim();
    if (trimmed !== (conversation.title ?? "Untitled conversation")) {
      await onRename(conversation.id, trimmed);
    }
  };

  const displayTitle = conversation.title ?? "Untitled conversation";

  return (
    <div
      className={cn(
        "group relative flex items-center px-3 py-1.5 text-sm rounded-md mx-1 cursor-pointer",
        isActive
          ? "bg-muted text-foreground"
          : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
      )}
    >
      {isEditing ? (
        <input
          ref={inputRef}
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onBlur={commitRename}
          onKeyDown={(e) => {
            if (e.key === "Enter") commitRename();
            if (e.key === "Escape") setIsEditing(false);
          }}
          className="flex-1 bg-transparent outline-none text-sm min-w-0"
        />
      ) : (
        <Link
          to={`/c/${conversation.id}`}
          className="flex-1 truncate no-underline text-inherit"
        >
          {displayTitle}
        </Link>
      )}

      {/* Hover menu trigger */}
      {!isEditing && (
        <button
          className={cn(
            "ml-1 shrink-0 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-foreground transition-opacity text-xs px-1",
            showMenu && "opacity-100"
          )}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setShowMenu((v) => !v);
          }}
        >
          •••
        </button>
      )}

      {/* Dropdown menu */}
      {showMenu && (
        <div
          ref={menuRef}
          className="absolute right-0 top-full mt-1 z-50 bg-popover border rounded-md shadow-md py-1 min-w-[120px]"
        >
          <button
            className="w-full text-left text-xs px-3 py-1.5 hover:bg-muted transition-colors"
            onClick={(e) => {
              e.preventDefault();
              setShowMenu(false);
              setIsEditing(true);
            }}
          >
            Rename
          </button>
          <button
            className="w-full text-left text-xs px-3 py-1.5 hover:bg-muted transition-colors text-destructive"
            onClick={(e) => {
              e.preventDefault();
              setShowMenu(false);
              onDelete(conversation.id);
            }}
          >
            Delete
          </button>
        </div>
      )}
    </div>
  );
}
