import { create } from "zustand";

import type {
  ReservationBridgeResponse,
  ReservationStatus,
} from "@/types/reservation";

interface ReservationState {
  reservation: ReservationBridgeResponse | null;
  liveStatus: ReservationStatus | null;
  liveRoom: string | null;
  setReservation: (reservation: ReservationBridgeResponse) => void;
  updateLiveStatus: (status: ReservationStatus, room?: string) => void;
  clearReservation: () => void;
}

export const useReservationStore = create<ReservationState>()((set) => ({
  reservation: null,
  liveStatus: null,
  liveRoom: null,
  setReservation: (reservation) =>
    set({ reservation, liveStatus: reservation.status, liveRoom: null }),
  updateLiveStatus: (status, room) =>
    set({ liveStatus: status, liveRoom: room ?? null }),
  clearReservation: () =>
    set({ reservation: null, liveStatus: null, liveRoom: null }),
}));
