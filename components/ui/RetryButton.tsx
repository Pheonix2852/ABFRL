import { Pressable, StyleSheet, Text } from "react-native";

import { displayValue } from "@/utils/displayValue";

type RetryButtonProps = {
  onPress: () => void;
  label?: string;
  disabled?: boolean;
};

export function RetryButton({ onPress, label = "Retry", disabled }: RetryButtonProps) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [
        styles.button,
        pressed && !disabled ? styles.buttonPressed : null,
        disabled ? styles.buttonDisabled : null,
      ]}
    >
      <Text style={styles.label}>{displayValue(label)}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    backgroundColor: "#13293d",
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 9,
    alignSelf: "flex-start",
  },
  buttonPressed: {
    opacity: 0.82,
  },
  buttonDisabled: {
    opacity: 0.45,
  },
  label: {
    color: "#f7f4ef",
    fontSize: 13,
    fontWeight: "700",
  },
});
