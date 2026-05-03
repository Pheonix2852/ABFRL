import { Ionicons } from "@expo/vector-icons";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { displayValue } from "@/utils/displayValue";

type HeaderProps = {
  title: string;
  showBack?: boolean;
  onBack?: () => void;
  rightActionLabel?: string;
  onRightAction?: () => void;
};

export function Header({
  title,
  showBack,
  onBack,
  rightActionLabel,
  onRightAction,
}: HeaderProps) {
  return (
    <View style={styles.wrapper}>
      <View style={styles.leftSection}>
        {showBack ? (
          <Pressable onPress={onBack} style={styles.backButton}>
            <Ionicons name="chevron-back" size={20} color="#13293d" />
          </Pressable>
        ) : null}
        <Text style={styles.title}>{displayValue(title)}</Text>
      </View>

      {rightActionLabel && onRightAction ? (
        <Pressable onPress={onRightAction} style={styles.rightAction}>
          <Text style={styles.rightActionText}>{displayValue(rightActionLabel)}</Text>
        </Pressable>
      ) : (
        <View style={styles.rightActionPlaceholder} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 12,
    minHeight: 44,
  },
  leftSection: {
    flexDirection: "row",
    alignItems: "center",
    flexShrink: 1,
  },
  backButton: {
    width: 34,
    height: 34,
    borderRadius: 17,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#efe8dc",
    marginRight: 8,
  },
  title: {
    color: "#13293d",
    fontSize: 22,
    fontWeight: "800",
    letterSpacing: 0.2,
  },
  rightAction: {
    backgroundColor: "#13293d",
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  rightActionText: {
    color: "#f7f4ef",
    fontSize: 12,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 0.7,
  },
  rightActionPlaceholder: {
    width: 48,
  },
});
