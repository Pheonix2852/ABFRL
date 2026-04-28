import { Pressable, StyleSheet, Text, View } from "react-native";
import { useEffect } from "react";
import { useRouter } from "expo-router";

import { Header } from "@/components/layout/Header";
import { ScreenWrapper } from "@/components/layout/ScreenWrapper";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useReservationStore } from "@/store/reservationStore";

export default function ReadyStateScreen() {
  const router = useRouter();

  const reservation = useReservationStore((state) => state.reservation);
  const liveRoom = useReservationStore((state) => state.liveRoom);
  const liveStatus = useReservationStore((state) => state.liveStatus);

  useEffect(() => {
    if (!reservation) {
      router.replace("/landing");
    }
  }, [reservation, router]);

  if (!reservation) {
    return null;
  }

  return (
    <ScreenWrapper>
      <Header title="Ready" />

      <View style={styles.card}>
        <Text style={styles.title}>Your items are ready.</Text>
        <Text style={styles.body}>
          {liveRoom
            ? `Please go to Room: ${liveRoom}`
            : "Room assignment pending. Please check with store staff."}
        </Text>

        <StatusBadge status={liveStatus ?? "ready"} />

        <Pressable onPress={() => router.push("/checkout-placeholder")} style={styles.cta}>
          <Text style={styles.ctaText}>Continue to Checkout</Text>
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
    color: "#1f6f34",
    fontWeight: "900",
  },
  body: {
    fontSize: 14,
    lineHeight: 21,
    color: "#2b3440",
  },
  cta: {
    marginTop: 12,
    backgroundColor: "#13293d",
    paddingVertical: 12,
    borderRadius: 12,
    alignItems: "center",
  },
  ctaText: {
    color: "#f7f4ef",
    fontWeight: "700",
    fontSize: 14,
  },
});
