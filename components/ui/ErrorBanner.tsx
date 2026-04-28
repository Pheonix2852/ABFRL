import { StyleSheet, Text, View } from "react-native";

import { RetryButton } from "@/components/ui/RetryButton";

type ErrorBannerProps = {
  message: string;
  onRetry?: () => void;
};

export function ErrorBanner({ message, onRetry }: ErrorBannerProps) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Something went wrong</Text>
      <Text style={styles.message}>{message}</Text>
      {onRetry ? <RetryButton onPress={onRetry} /> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#ffe2dc",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#f2a79d",
    padding: 12,
    gap: 8,
  },
  title: {
    fontSize: 14,
    fontWeight: "800",
    color: "#8e2f23",
  },
  message: {
    fontSize: 13,
    color: "#8e2f23",
    lineHeight: 18,
  },
});
