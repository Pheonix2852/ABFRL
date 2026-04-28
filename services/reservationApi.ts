import { RESERVATION_ENDPOINT } from "@/constants/config";
import type {
  ReservationBridgeRequest,
  ReservationBridgeResponse,
} from "@/types/reservation";

export async function createReservation(
  payload: ReservationBridgeRequest,
): Promise<ReservationBridgeResponse> {
  if (RESERVATION_ENDPOINT.includes("PLACEHOLDER")) {
    throw new Error(
      "[reservationApi] Reservation endpoint not configured. " +
        "Update EXPO_PUBLIC_RESERVATION_ENDPOINT in .env before using this feature.",
    );
  }

  const response = await fetch(RESERVATION_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Reservation API error: ${response.status}`);
  }

  return (await response.json()) as ReservationBridgeResponse;
}
