import { create } from "zustand";

export interface ActiveQueryContext {
  gender: string | null;
  category: string | null;
  subcategory: string | null;
  budget_min: number | null;
  budget_max: number | null;
  occasion: string | null;
  color: string | null;
}

interface ActiveQueryState {
  context: ActiveQueryContext;
  setContext: (patch: Partial<ActiveQueryContext>) => void;
  resetContext: () => void;
}

const DEFAULT_CONTEXT: ActiveQueryContext = {
  gender: null,
  category: null,
  subcategory: null,
  budget_min: null,
  budget_max: null,
  occasion: null,
  color: null,
};

export const useActiveQueryStore = create<ActiveQueryState>((set) => ({
  context: DEFAULT_CONTEXT,
  setContext: (patch) => set((state) => ({ context: { ...state.context, ...patch } })),
  resetContext: () => set({ context: DEFAULT_CONTEXT }),
}));
