import { useEffect, useMemo, useState } from "react";
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from "react-native";
import { useRouter } from "expo-router";

import { Header } from "@/components/layout/Header";
import { ScreenWrapper } from "@/components/layout/ScreenWrapper";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { ProductCard } from "@/components/ui/ProductCard";
import { buildAugmentedMessage, sendChatMessageWithRetry } from "@/services/chatApi";
import { createReservation } from "@/services/reservationApi";
import { useActiveQueryStore } from "@/store/activeQueryStore";
import { useChatStore } from "@/store/chatStore";
import { useReservationStore } from "@/store/reservationStore";
import { useSessionStore } from "@/store/sessionStore";
import { useUserProfileStore } from "@/store/userProfileStore";
import { filterProductsByContext } from "@/utils/productValidator";

export default function RecommendationsScreen() {
  const router = useRouter();
  const { products } = useChatStore();
  const metadata = useChatStore((state) => state.metadata);
  const latestIntent = useChatStore((state) => state.latestIntent);
  const setProducts = useChatStore((state) => state.setProducts);
  const sessionId = useSessionStore((state) => state.sessionId);
  const setReservation = useReservationStore((state) => state.setReservation);
  const profile = useUserProfileStore((state) => state.profile);
  const activeContext = useActiveQueryStore((state) => state.context);

  const [error, setError] = useState<string | null>(null);
  const [pendingProductId, setPendingProductId] = useState<string | null>(null);
  const [autoRetrying, setAutoRetrying] = useState(false);

  const { valid, filtered } = useMemo(
    () => filterProductsByContext(products, activeContext),
    [activeContext, products],
  );

  useEffect(() => {
    const shouldRetry =
      latestIntent === "recommendation" &&
      valid.length === 0 &&
      filtered.length > 0 &&
      !autoRetrying;
    if (!shouldRetry || !profile) {
      return;
    }

    const retryMessage = buildAugmentedMessage("More", activeContext);
    setAutoRetrying(true);

    void sendChatMessageWithRetry({
      message: retryMessage,
      user_id: profile.user_id,
      session_id: sessionId,
    })
      .then((response) => {
        setProducts(response.products ?? []);
      })
      .catch((retryError) => {
        setError(
          retryError instanceof Error
            ? retryError.message
            : "Unable to refresh recommendations.",
        );
      })
      .finally(() => setAutoRetrying(false));
  }, [
    activeContext,
    autoRetrying,
    filtered.length,
    latestIntent,
    profile,
    sessionId,
    setProducts,
    valid.length,
  ]);

  const handleReserve = async (productId: string) => {
    setError(null);
    setPendingProductId(productId);

    try {
      if (!profile) {
        throw new Error("Profile not ready. Please try again.");
      }

      const reservation = await createReservation({
        user_id: profile.user_id,
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

      {metadata?.loyalty_tier && typeof metadata.loyalty_discount_pct === "number" ? (
        <View style={styles.loyaltyBanner}>
          <Text style={styles.loyaltyText}>
            {`${metadata.loyalty_tier.toUpperCase()} Member - ${metadata.loyalty_discount_pct}% Benefit Applied`}
          </Text>
        </View>
      ) : null}

      {error ? <ErrorBanner message={error} /> : null}

      {valid.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyTitle}>No products yet</Text>
          <Text style={styles.emptyCopy}>
            Ask for more details in chat and then come back to recommendations.
          </Text>
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.listWrap}>
          {valid.map((product) => (
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
  loyaltyBanner: {
    marginTop: 10,
    alignSelf: "flex-start",
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 7,
    backgroundColor: "#efe4cf",
    borderWidth: 1,
    borderColor: "#cfb78e",
  },
  loyaltyText: {
    fontSize: 12,
    fontWeight: "800",
    color: "#4b3f2a",
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
