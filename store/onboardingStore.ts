import { create } from "zustand";

import type { OnboardingAnswers } from "@/types/onboarding";

interface OnboardingState {
  answers: OnboardingAnswers | null;
  initialPrompt: string | null;
  setAnswers: (answers: OnboardingAnswers) => void;
  setInitialPrompt: (prompt: string) => void;
  clearInitialPrompt: () => void;
  clearAnswers: () => void;
}

export const useOnboardingStore = create<OnboardingState>()((set) => ({
  answers: null,
  initialPrompt: null,
  setAnswers: (answers) => set({ answers }),
  setInitialPrompt: (prompt) => set({ initialPrompt: prompt }),
  clearInitialPrompt: () => set({ initialPrompt: null }),
  clearAnswers: () => set({ answers: null, initialPrompt: null }),
}));
