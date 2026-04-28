import AsyncStorage from "@react-native-async-storage/async-storage";
import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

interface SessionState {
  sessionId: string | null;
  setSessionId: (id: string) => void;
  resetSession: () => void;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      sessionId: null,
      setSessionId: (id) => set({ sessionId: id }),
      resetSession: () => set({ sessionId: null }),
    }),
    {
      name: "chat-session",
      storage: createJSONStorage(() => AsyncStorage),
    },
  ),
);
