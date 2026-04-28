import { StyleSheet, Text, View } from "react-native";

import type { ReservationStatus } from "@/types/reservation";

type StatusBadgeProps = {
  status: ReservationStatus;
};

const STATUS_STYLE: Record<ReservationStatus, { bg: string; fg: string; label: string }> = {
  waiting: { bg: "#ffefcf", fg: "#734f00", label: "Waiting" },
  ready: { bg: "#d7f7de", fg: "#1f6f34", label: "Ready" },
  completed: { bg: "#e5e8eb", fg: "#3f4954", label: "Completed" },
  cancelled: { bg: "#efe3f4", fg: "#5e2f75", label: "Cancelled" },
  expired: { bg: "#fbd9d9", fg: "#7c1f1f", label: "Expired" },
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const style = STATUS_STYLE[status];

  return (
    <View style={[styles.badge, { backgroundColor: style.bg }]}>
      <Text style={[styles.label, { color: style.fg }]}>{style.label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 6,
    alignSelf: "flex-start",
  },
  label: {
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 0.2,
  },
});
