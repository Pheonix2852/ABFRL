export type ReservationStatus =
  | "waiting"
  | "ready"
  | "completed"
  | "cancelled"
  | "expired";

export interface ReservationRecord {
  reservation_id: string;
  user_id: string;
  product_ids: string[];
  status: ReservationStatus;
  room?: string;
  qr_payload: string;
  qr_code_url?: string;
  created_at: string;
  updated_at: string;
}

export interface ReservationBridgeRequest {
  user_id: string;
  product_id: string;
  session_id?: string;
}

export interface ReservationBridgeResponse {
  reservation_id: string;
  status: ReservationStatus;
  qr_payload: string;
  qr_code_url?: string;
}
