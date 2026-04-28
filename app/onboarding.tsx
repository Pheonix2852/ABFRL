import { useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { useRouter } from "expo-router";

import { Header } from "@/components/layout/Header";
import { ScreenWrapper } from "@/components/layout/ScreenWrapper";
import { useOnboardingStore } from "@/store/onboardingStore";
import type { BudgetRange, OccasionType } from "@/types/onboarding";

const BUDGET_OPTIONS: BudgetRange[] = [
  { min: 0, max: 2000, label: "Under Rs.2000" },
  { min: 2000, max: 5000, label: "Rs.2000 - Rs.5000" },
  { min: 5000, max: 99999, label: "Rs.5000+" },
];

const COLOR_OPTIONS = ["Red", "Blue", "Gold", "White", "Black", "Green", "Pink"];

const OCCASION_OPTIONS: { label: string; value: OccasionType }[] = [
  { label: "Gifting", value: "gifting" },
  { label: "Self-wear", value: "self_wear" },
  { label: "Family celebration", value: "family" },
];

export default function OnboardingScreen() {
  const router = useRouter();
  const { setAnswers, setInitialPrompt } = useOnboardingStore();

  const [step, setStep] = useState(0);
  const [selectedBudget, setSelectedBudget] = useState<BudgetRange | null>(null);
  const [selectedColors, setSelectedColors] = useState<string[]>([]);
  const [selectedOccasion, setSelectedOccasion] = useState<OccasionType | null>(null);

  const canContinue = useMemo(() => {
    if (step === 0) {
      return Boolean(selectedBudget);
    }

    if (step === 1) {
      return selectedColors.length > 0;
    }

    return Boolean(selectedOccasion);
  }, [selectedBudget, selectedColors, selectedOccasion, step]);

  const toggleColor = (color: string) => {
    setSelectedColors((prev) =>
      prev.includes(color) ? prev.filter((entry) => entry !== color) : [...prev, color],
    );
  };

  const handleNext = () => {
    if (!canContinue) {
      return;
    }

    if (step < 2) {
      setStep((prev) => prev + 1);
      return;
    }

    if (!selectedBudget || !selectedOccasion) {
      return;
    }

    const answers = {
      budget: selectedBudget,
      colors: selectedColors,
      occasion: selectedOccasion,
    };

    setAnswers(answers);

    const firstPrompt = `I am looking for ${selectedOccasion} outfits in ${selectedColors.join(", ")}, budget ${selectedBudget.label}`;
    setInitialPrompt(firstPrompt);

    router.push("/chat");
  };

  return (
    <ScreenWrapper>
      <Header title="Onboarding" showBack onBack={() => router.back()} />

      <View style={styles.card}>
        <Text style={styles.stepLabel}>Step {step + 1} of 3</Text>

        {step === 0 ? (
          <>
            <Text style={styles.question}>What is your budget range?</Text>
            <View style={styles.optionsWrap}>
              {BUDGET_OPTIONS.map((option) => {
                const active = selectedBudget?.label === option.label;
                return (
                  <Pressable
                    key={option.label}
                    style={[styles.optionPill, active && styles.optionPillActive]}
                    onPress={() => setSelectedBudget(option)}
                  >
                    <Text style={[styles.optionText, active && styles.optionTextActive]}>
                      {option.label}
                    </Text>
                  </Pressable>
                );
              })}
            </View>
          </>
        ) : null}

        {step === 1 ? (
          <>
            <Text style={styles.question}>Choose your preferred colors</Text>
            <View style={styles.optionsWrap}>
              {COLOR_OPTIONS.map((color) => {
                const active = selectedColors.includes(color);
                return (
                  <Pressable
                    key={color}
                    style={[styles.optionPill, active && styles.optionPillActive]}
                    onPress={() => toggleColor(color)}
                  >
                    <Text style={[styles.optionText, active && styles.optionTextActive]}>{color}</Text>
                  </Pressable>
                );
              })}
            </View>
          </>
        ) : null}

        {step === 2 ? (
          <>
            <Text style={styles.question}>What is this for?</Text>
            <View style={styles.optionsWrap}>
              {OCCASION_OPTIONS.map((option) => {
                const active = selectedOccasion === option.value;
                return (
                  <Pressable
                    key={option.value}
                    style={[styles.optionPill, active && styles.optionPillActive]}
                    onPress={() => setSelectedOccasion(option.value)}
                  >
                    <Text style={[styles.optionText, active && styles.optionTextActive]}>
                      {option.label}
                    </Text>
                  </Pressable>
                );
              })}
            </View>
          </>
        ) : null}
      </View>

      <Pressable
        disabled={!canContinue}
        onPress={handleNext}
        style={[styles.nextButton, !canContinue && styles.nextButtonDisabled]}
      >
        <Text style={styles.nextButtonText}>{step === 2 ? "Start Chat" : "Next"}</Text>
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
    gap: 16,
  },
  stepLabel: {
    fontSize: 12,
    color: "#6f7881",
    textTransform: "uppercase",
    letterSpacing: 0.7,
    fontWeight: "700",
  },
  question: {
    fontSize: 25,
    fontWeight: "800",
    lineHeight: 32,
    color: "#13293d",
  },
  optionsWrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
  },
  optionPill: {
    borderWidth: 1,
    borderColor: "#e1d4c4",
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 10,
    backgroundColor: "#f7f1e7",
  },
  optionPillActive: {
    backgroundColor: "#13293d",
    borderColor: "#13293d",
  },
  optionText: {
    fontSize: 13,
    fontWeight: "700",
    color: "#2b3440",
  },
  optionTextActive: {
    color: "#f6f7fa",
  },
  nextButton: {
    marginTop: 12,
    borderRadius: 14,
    backgroundColor: "#d56a00",
    alignItems: "center",
    paddingVertical: 12,
  },
  nextButtonDisabled: {
    opacity: 0.35,
  },
  nextButtonText: {
    color: "#fff",
    fontWeight: "800",
    fontSize: 15,
  },
});
