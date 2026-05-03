import QRCode from "react-native-qrcode-svg";
import { StyleSheet, Text, View } from "react-native";

import { displayValue } from "@/utils/displayValue";

type ReservationQRProps = {
  qrPayload: string;
  reservationId: string;
};

export function ReservationQR({ qrPayload, reservationId }: ReservationQRProps) {
  return (
    <View style={styles.card}>
      <Text style={styles.title}>Reservation QR</Text>
      <View style={styles.qrWrap}>
        <QRCode value={qrPayload} size={210} />
      </View>
      <Text style={styles.id}>ID: {displayValue(reservationId)}</Text>
      <Text style={styles.helper}>Scan at store entrance</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#fff",
    borderRadius: 18,
    padding: 16,
    borderWidth: 1,
    borderColor: "#eadfcd",
    alignItems: "center",
    gap: 10,
  },
  title: {
    fontSize: 18,
    fontWeight: "800",
    color: "#13293d",
  },
  qrWrap: {
    padding: 14,
    backgroundColor: "#faf7f2",
    borderRadius: 12,
  },
  id: {
    fontSize: 14,
    color: "#2b3440",
    fontWeight: "600",
  },
  helper: {
    color: "#58616b",
    fontSize: 12,
  },
});
