import { useEffect, useState } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { useRouter } from "expo-router";

import { Header } from "@/components/layout/Header";
import { ScreenWrapper } from "@/components/layout/ScreenWrapper";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { ReservationQR } from "@/components/ui/ReservationQR";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { subscribeToReservation } from "@/services/firebaseClient";
import { useReservationStore } from "@/store/reservationStore";

export default function ReservationHandoffScreen() {
  const router = useRouter();

  const reservation = useReservationStore((state) => state.reservation);
  const liveStatus = useReservationStore((state) => state.liveStatus);
  const liveRoom = useReservationStore((state) => state.liveRoom);
  const updateLiveStatus = useReservationStore((state) => state.updateLiveStatus);

  const [listenerError, setListenerError] = useState<string | null>(null);
  const [listenerAttempt, setListenerAttempt] = useState(0);

  useEffect(() => {
    if (!reservation) {
      router.replace("/landing");
      return;
    }

    const unsubscribe = subscribeToReservation(
      reservation.reservation_id,
      (status, room) => {
        setListenerError(null);
        updateLiveStatus(status, room);

        if (status === "ready") {
          router.replace("/ready-state");
        }
      },
      (error) => {
        setListenerError(error.message || "Live listener disconnected");
      },
    );

    return unsubscribe;
  }, [listenerAttempt, reservation, router, updateLiveStatus]);

  if (!reservation) {
    return null;
  }

  const effectiveStatus = liveStatus ?? reservation.status;

  return (
    <ScreenWrapper>
      <Header title="Reservation Handoff" />

      <View style={styles.card}>
        <ReservationQR
          qrPayload={reservation.qr_payload}
          reservationId={reservation.reservation_id}
        />

        <View style={styles.statusArea}>
          <StatusBadge status={effectiveStatus} />
          <Text style={styles.statusText}>Waiting for store confirmation...</Text>
          {liveRoom ? <Text style={styles.roomText}>Assigned room: {liveRoom}</Text> : null}
          <ActivityIndicator color="#13293d" />
        </View>
      </View>

      {listenerError ? (
        <ErrorBanner
          message={listenerError}
          onRetry={() => setListenerAttempt((prev) => prev + 1)}
        />
      ) : null}
    </ScreenWrapper>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#fffdfa",
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "#eadfcd",
    padding: 14,
    gap: 12,
  },
  statusArea: {
    gap: 8,
    alignItems: "flex-start",
  },
  statusText: {
    color: "#33414e",
    fontSize: 14,
    fontWeight: "600",
  },
  roomText: {
    color: "#1f6f34",
    fontSize: 13,
    fontWeight: "700",
  },
});
