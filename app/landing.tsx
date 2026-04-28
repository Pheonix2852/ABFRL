import { useMemo } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { useRouter } from "expo-router";

import { Header } from "@/components/layout/Header";
import { ScreenWrapper } from "@/components/layout/ScreenWrapper";
import { getActiveFestiveEvent } from "@/constants/festiveCalendar";

export default function LandingScreen() {
  const router = useRouter();
  const activeEvent = useMemo(() => getActiveFestiveEvent(), []);

  return (
    <ScreenWrapper>
      <Header title="ABFRL Stylist" />

      <View style={styles.hero}>
        <View style={styles.badgeRow}>
          <View style={styles.dot} />
          <Text style={styles.badgeText}>Shopper Assistant</Text>
        </View>

        <Text style={styles.title}>Find your next look in a few guided turns</Text>

        <Text style={styles.subtitle}>
          {activeEvent?.triggerMessage ?? "Welcome. Let us find something perfect for you."}
        </Text>

        <Pressable onPress={() => router.push("/onboarding")} style={styles.ctaButton}>
          <Text style={styles.ctaText}>Get Started</Text>
        </Pressable>
      </View>

      <View style={styles.bottomMood}>
        <View style={styles.ellipseA} />
        <View style={styles.ellipseB} />
      </View>
    </ScreenWrapper>
  );
}

const styles = StyleSheet.create({
  hero: {
    flex: 1,
    backgroundColor: "#13293d",
    borderRadius: 28,
    padding: 22,
    justifyContent: "center",
    gap: 16,
    overflow: "hidden",
  },
  badgeRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#f6a23c",
  },
  badgeText: {
    color: "#f6a23c",
    fontWeight: "700",
    fontSize: 13,
    letterSpacing: 0.8,
    textTransform: "uppercase",
  },
  title: {
    color: "#f7f4ef",
    fontSize: 34,
    fontWeight: "900",
    lineHeight: 40,
  },
  subtitle: {
    color: "#dfe6ee",
    fontSize: 16,
    lineHeight: 23,
    maxWidth: 280,
  },
  ctaButton: {
    marginTop: 8,
    alignSelf: "flex-start",
    backgroundColor: "#f6a23c",
    borderRadius: 999,
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  ctaText: {
    color: "#1f2a34",
    fontWeight: "800",
    fontSize: 15,
  },
  bottomMood: {
    height: 84,
    marginTop: 12,
    position: "relative",
    overflow: "hidden",
  },
  ellipseA: {
    position: "absolute",
    width: 190,
    height: 190,
    borderRadius: 95,
    backgroundColor: "#f6a23c33",
    left: -20,
    top: -75,
  },
  ellipseB: {
    position: "absolute",
    width: 220,
    height: 220,
    borderRadius: 110,
    backgroundColor: "#13293d1f",
    right: -30,
    top: -92,
  },
});
