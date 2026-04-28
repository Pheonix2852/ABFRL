import { create } from "zustand";

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
  setProducts: (products: Product[]) => void;
  addMessage: (message: ChatMessage) => void;
  clearMessages: () => void;
  clearProducts: () => void;
  clearChat: () => void;
}

export const useChatStore = create<ChatState>()((set) => ({
  messages: [],
  products: [],
  setProducts: (products) => set({ products }),
  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),
  clearMessages: () => set({ messages: [] }),
  clearProducts: () => set({ products: [] }),
  clearChat: () => set({ messages: [], products: [] }),
}));
