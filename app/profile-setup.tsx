import { useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { useRouter } from "expo-router";

import { Header } from "@/components/layout/Header";
import { ScreenWrapper } from "@/components/layout/ScreenWrapper";
import { useUserProfileStore } from "@/store/userProfileStore";

function createUserId(): string {
  return `user_${Date.now()}_${Math.random().toString(16).slice(2, 10)}`;
}

export default function ProfileSetupScreen() {
  const router = useRouter();
  const setProfile = useUserProfileStore((state) => state.setProfile);

  const [name, setName] = useState("");

  const handleContinue = () => {
    const trimmed = name.trim();
    const displayName = trimmed.length > 0 ? trimmed : "Guest";

    setProfile({
      user_id: createUserId(),
      display_name: displayName,
      is_profile_complete: false,
      loyalty_tier: "bronze",
    });

    router.replace("/onboarding");
  };

  return (
    <ScreenWrapper>
      <Header title="Profile" />

      <View style={styles.card}>
        <Text style={styles.title}>Let’s set up your profile</Text>
        <Text style={styles.subtitle}>
          Tell us your name so your stylist can personalize recommendations.
        </Text>
        <TextInput
          value={name}
          onChangeText={setName}
          placeholder="Enter your name"
          placeholderTextColor="#8d949c"
          style={styles.input}
        />
      </View>

      <Pressable onPress={handleContinue} style={styles.ctaButton}>
        <Text style={styles.ctaText}>Continue</Text>
      </Pressable>
    </ScreenWrapper>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    borderRadius: 22,
    backgroundColor: "#fffdfa",
    borderWidth: 1,
    borderColor: "#eadfcd",
    padding: 16,
    gap: 12,
  },
  title: {
    fontSize: 24,
    fontWeight: "800",
    color: "#13293d",
  },
  subtitle: {
    fontSize: 14,
    color: "#47505a",
    lineHeight: 20,
  },
  input: {
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#ddd2c4",
    paddingHorizontal: 12,
    paddingVertical: 10,
    backgroundColor: "#fffdfa",
    color: "#1f2a34",
  },
  ctaButton: {
    marginTop: 12,
    borderRadius: 14,
    backgroundColor: "#d56a00",
    alignItems: "center",
    paddingVertical: 12,
  },
  ctaText: {
    color: "#fff",
    fontWeight: "800",
    fontSize: 15,
  },
});
