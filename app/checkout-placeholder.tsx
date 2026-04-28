import { useEffect } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { useRouter } from "expo-router";

import { Header } from "@/components/layout/Header";
import { ScreenWrapper } from "@/components/layout/ScreenWrapper";
import { useChatStore } from "@/store/chatStore";
import { useOnboardingStore } from "@/store/onboardingStore";
import { useReservationStore } from "@/store/reservationStore";
import { useSessionStore } from "@/store/sessionStore";

export default function CheckoutPlaceholderScreen() {
  const router = useRouter();

  const reservation = useReservationStore((state) => state.reservation);
  const clearReservation = useReservationStore((state) => state.clearReservation);
  const clearOnboarding = useOnboardingStore((state) => state.clearAnswers);
  const clearChat = useChatStore((state) => state.clearChat);
  const resetSession = useSessionStore((state) => state.resetSession);

  useEffect(() => {
    if (!reservation) {
      router.replace("/landing");
    }
  }, [reservation, router]);

  if (!reservation) {
    return null;
  }

  const handleDone = () => {
    clearReservation();
    clearOnboarding();
    clearChat();
    resetSession();

    router.replace("/landing");
  };

  return (
    <ScreenWrapper>
      <Header title="Checkout" />

      <View style={styles.card}>
        <Text style={styles.title}>Checkout coming soon</Text>
        <Text style={styles.body}>
          Your items are reserved and waiting for you. This v1 screen is a placeholder and
          intentionally does not include payment logic.
        </Text>

        <View style={styles.summary}>
          <Text style={styles.summaryLabel}>Reservation ID</Text>
          <Text style={styles.summaryValue}>{reservation.reservation_id}</Text>
        </View>

        <Pressable onPress={handleDone} style={styles.button}>
          <Text style={styles.buttonText}>Done</Text>
        </Pressable>
      </View>
    </ScreenWrapper>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#fffdfa",
    borderWidth: 1,
    borderColor: "#eadfcd",
    borderRadius: 20,
    padding: 18,
    gap: 12,
  },
  title: {
    fontSize: 30,
    lineHeight: 36,
    color: "#13293d",
    fontWeight: "900",
  },
  body: {
    fontSize: 14,
    lineHeight: 21,
    color: "#3d4854",
  },
  summary: {
    marginTop: 8,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#e7ddce",
    padding: 12,
    gap: 4,
  },
  summaryLabel: {
    color: "#6f7881",
    fontSize: 12,
    textTransform: "uppercase",
    letterSpacing: 0.8,
    fontWeight: "700",
  },
  summaryValue: {
    color: "#13293d",
    fontSize: 15,
    fontWeight: "700",
  },
  button: {
    marginTop: 12,
    borderRadius: 12,
    paddingVertical: 12,
    backgroundColor: "#d56a00",
    alignItems: "center",
  },
  buttonText: {
    color: "#fff",
    fontSize: 14,
    fontWeight: "800",
  },
});
