import AsyncStorage from "@react-native-async-storage/async-storage";
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export type LoyaltyTier = "bronze" | "silver" | "gold" | "platinum";

export interface UserProfile {
  user_id: string;
  display_name: string;
  is_profile_complete: boolean;
  loyalty_tier?: LoyaltyTier;
}

interface UserProfileState {
  profile: UserProfile | null;
  setProfile: (profile: UserProfile) => void;
  updateProfile: (patch: Partial<UserProfile>) => void;
  clearProfile: () => void;
}

export const useUserProfileStore = create<UserProfileState>()(
  persist(
    (set, get) => ({
      profile: null,
      setProfile: (profile) => set({ profile }),
      updateProfile: (patch) => {
        const current = get().profile;
        if (!current) return;
        set({ profile: { ...current, ...patch } });
      },
      clearProfile: () => set({ profile: null }),
    }),
    {
      name: "abfrl-user-profile",
      storage: createJSONStorage(() => AsyncStorage),
    }
  )
);
