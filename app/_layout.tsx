import { Stack, useRouter } from "expo-router";
import { useEffect } from "react";

import { AppErrorBoundary } from "@/components/AppErrorBoundary";
import { useChatStore } from "@/store/chatStore";
import { useOnboardingStore } from "@/store/onboardingStore";
import { useReservationStore } from "@/store/reservationStore";
import { useSessionStore } from "@/store/sessionStore";
import { validateEnv } from "@/utils/validateEnv";

export default function RootLayout() {
  const router = useRouter();

  useEffect(() => {
    validateEnv();
  }, []);

  const handleAppReset = () => {
    useSessionStore.getState().resetSession();
    useOnboardingStore.getState().clearAnswers();
    useChatStore.getState().clearChat();
    useReservationStore.getState().clearReservation();
    router.replace("/landing");
  };

  return (
    <AppErrorBoundary onReset={handleAppReset}>
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="index" />
        <Stack.Screen name="landing" />
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
