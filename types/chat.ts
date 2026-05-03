import type { Product } from "@/types/product";

export interface ChatRequest {
  message: string;
  user_id: string;
  session_id: string | null;
}

export interface ChatMetadata {
  loyalty_tier?: "bronze" | "silver" | "gold" | "platinum";
  loyalty_discount_pct?: number;
  cta?: string;
  resolved_sku?: string;
  store?: string;
  store_label?: string;
}

export interface ChatResponse {
  session_id: string;
  message: string;
  intent: string;
  products?: Product[];
  metadata?: ChatMetadata | null;
  error?: string | null;
}
