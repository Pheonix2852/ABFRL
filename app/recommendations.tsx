import { useState } from "react";
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from "react-native";
import { useRouter } from "expo-router";

import { Header } from "@/components/layout/Header";
import { ScreenWrapper } from "@/components/layout/ScreenWrapper";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { ProductCard } from "@/components/ui/ProductCard";
import { DEV_USER_ID } from "@/constants/config";
import { createReservation } from "@/services/reservationApi";
import { useChatStore } from "@/store/chatStore";
import { useReservationStore } from "@/store/reservationStore";
import { useSessionStore } from "@/store/sessionStore";

export default function RecommendationsScreen() {
  const router = useRouter();
  const { products } = useChatStore();
  const sessionId = useSessionStore((state) => state.sessionId);
  const setReservation = useReservationStore((state) => state.setReservation);

  const [error, setError] = useState<string | null>(null);
  const [pendingProductId, setPendingProductId] = useState<string | null>(null);

  const handleReserve = async (productId: string) => {
    setError(null);
    setPendingProductId(productId);

    try {
      const reservation = await createReservation({
        user_id: DEV_USER_ID,
        product_id: productId,
        session_id: sessionId ?? undefined,
      });

      setReservation(reservation);
      router.push("/reservation-handoff");
    } catch (reservationError) {
      setError(
        reservationError instanceof Error
          ? reservationError.message
          : "Reservation failed. Please try again.",
      );
    } finally {
      setPendingProductId(null);
    }
  };

  return (
    <ScreenWrapper>
      <Header title="Recommendations" showBack onBack={() => router.back()} />

      {error ? <ErrorBanner message={error} /> : null}

      {products.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyTitle}>No products yet</Text>
          <Text style={styles.emptyCopy}>
            Ask for more details in chat and then come back to recommendations.
          </Text>
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.listWrap}>
          {products.map((product) => (
            <ProductCard
              key={product.id}
              product={product}
              onReserve={handleReserve}
              reserving={pendingProductId === product.id}
            />
          ))}
          {pendingProductId ? (
            <View style={styles.pendingRow}>
              <ActivityIndicator color="#13293d" />
              <Text style={styles.pendingText}>Creating reservation...</Text>
            </View>
          ) : null}
        </ScrollView>
      )}
    </ScreenWrapper>
  );
}

const styles = StyleSheet.create({
  listWrap: {
    paddingTop: 10,
    paddingBottom: 24,
  },
  emptyState: {
    marginTop: 20,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#eadfcd",
    backgroundColor: "#fffdfa",
    padding: 18,
    gap: 8,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: "800",
    color: "#13293d",
  },
  emptyCopy: {
    color: "#47505a",
    fontSize: 14,
    lineHeight: 20,
  },
  pendingRow: {
    marginTop: 6,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  pendingText: {
    color: "#33414e",
    fontSize: 13,
    fontWeight: "600",
  },
});
