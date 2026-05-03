import { create } from "zustand";

import type { ChatMetadata } from "@/types/chat";
import type { Product } from "@/types/product";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  timestamp: string;
}

interface ChatState {
  messages: ChatMessage[];
  products: Product[];
  metadata: ChatMetadata | null;
  latestIntent: string | null;
  setProducts: (products: Product[]) => void;
  setMetadata: (metadata: ChatMetadata | null) => void;
  setLatestIntent: (intent: string | null) => void;
  addMessage: (message: ChatMessage) => void;
  clearMessages: () => void;
  clearProducts: () => void;
  clearChat: () => void;
}

export const useChatStore = create<ChatState>()((set) => ({
  messages: [],
  products: [],
  metadata: null,
  latestIntent: null,
  setProducts: (products) => set({ products }),
  setMetadata: (metadata) => set({ metadata }),
  setLatestIntent: (latestIntent) => set({ latestIntent }),
  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),
  clearMessages: () => set({ messages: [] }),
  clearProducts: () => set({ products: [] }),
  clearChat: () => set({ messages: [], products: [], metadata: null, latestIntent: null }),
}));
