"use client";

import { useCallback, useEffect, useState } from "react";
import type { ChatHistoryEntry } from "@/types/api";

const STORAGE_KEY = "bayyinah_chat_history";

export function useChatHistory() {
  const [history, setHistory] = useState<ChatHistoryEntry[]>([]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setHistory(JSON.parse(raw));
    } catch {
      // ignore corrupted storage
    }
  }, []);

  const addEntry = useCallback((entry: ChatHistoryEntry) => {
    setHistory((prev) => {
      const next = [entry, ...prev].slice(0, 100);
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        // storage full or unavailable
      }
      return next;
    });
  }, []);

  const clearHistory = useCallback(() => {
    setHistory([]);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // ignore
    }
  }, []);

  return { history, addEntry, clearHistory };
}
