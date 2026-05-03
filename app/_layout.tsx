import "react-native-get-random-values";

import { Stack } from "expo-router";
import { useEffect } from "react";

import { AppErrorBoundary } from "@/components/AppErrorBoundary";
import { useChatStore } from "@/store/chatStore";
import { useActiveQueryStore } from "@/store/activeQueryStore";
import { useOnboardingStore } from "@/store/onboardingStore";
import { useReservationStore } from "@/store/reservationStore";
import { useSessionStore } from "@/store/sessionStore";
import { useUserProfileStore } from "@/store/userProfileStore";
import { validateEnv } from "@/utils/validateEnv";

export default function RootLayout() {
  useEffect(() => {
    validateEnv();

    if (__DEV__) handleAppReset();
  }, []);

  const handleAppReset = () => {
    useSessionStore.getState().resetSession();
    useOnboardingStore.getState().clearAnswers();
    useChatStore.getState().clearChat();
    useActiveQueryStore.getState().resetContext();
    useReservationStore.getState().clearReservation();
    useUserProfileStore.getState().clearProfile();
  };

  

  return (
    <AppErrorBoundary onReset={handleAppReset}>
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="index" />
        <Stack.Screen name="landing" />
        <Stack.Screen name="profile-setup" />
        <Stack.Screen name="onboarding" />
        <Stack.Screen name="chat" />
        <Stack.Screen name="recommendations" />
        <Stack.Screen name="reservation-handoff" />
        <Stack.Screen name="ready-state" />
        <Stack.Screen name="checkout-placeholder" />
      </Stack>
    </AppErrorBoundary>
  );
}