import { useCallback, useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";

export interface Conversation {
  id: string;
  title: string | null;
  updated_at: string;
}

export interface ConversationGroup {
  label: string;
  items: Conversation[];
}

function groupByDate(conversations: Conversation[]): ConversationGroup[] {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400_000);
  const sevenDaysAgo = new Date(today.getTime() - 7 * 86400_000);
  const thirtyDaysAgo = new Date(today.getTime() - 30 * 86400_000);

  const groups: { label: string; items: Conversation[] }[] = [
    { label: "Today", items: [] },
    { label: "Yesterday", items: [] },
    { label: "Previous 7 days", items: [] },
    { label: "Previous 30 days", items: [] },
    { label: "Older", items: [] },
  ];

  for (const c of conversations) {
    const d = new Date(c.updated_at);
    if (d >= today) {
      groups[0].items.push(c);
    } else if (d >= yesterday) {
      groups[1].items.push(c);
    } else if (d >= sevenDaysAgo) {
      groups[2].items.push(c);
    } else if (d >= thirtyDaysAgo) {
      groups[3].items.push(c);
    } else {
      groups[4].items.push(c);
    }
  }

  return groups.filter((g) => g.items.length > 0);
}

export function useConversations() {
  const [groups, setGroups] = useState<ConversationGroup[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchConversations = useCallback(async () => {
    const { data, error } = await supabase
      .from("conversations")
      .select("id, title, updated_at")
      .order("updated_at", { ascending: false })
      .limit(100);

    if (!error && data) {
      setGroups(groupByDate(data as Conversation[]));
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchConversations();

    // Re-fetch when tab becomes visible (cross-tab sync)
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        fetchConversations();
      }
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () =>
      document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, [fetchConversations]);

  const renameConversation = useCallback(
    async (id: string, title: string) => {
      await supabase
        .from("conversations")
        .update({ title: title.trim() || null })
        .eq("id", id);
      await fetchConversations();
    },
    [fetchConversations]
  );

  const deleteConversation = useCallback(
    async (id: string) => {
      await supabase.from("conversations").delete().eq("id", id);
      await fetchConversations();
    },
    [fetchConversations]
  );

  return {
    groups,
    loading,
    refetch: fetchConversations,
    renameConversation,
    deleteConversation,
  };
}
