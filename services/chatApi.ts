import { CHAT_ENDPOINT } from "@/constants/config";
import type { ChatRequest, ChatResponse } from "@/types/chat";
import type { Product } from "@/types/product";

const REQUEST_TIMEOUT_MS = 10000;

function isValidProduct(item: unknown): item is Product {
  if (!item || typeof item !== "object") {
    return false;
  }

  const candidate = item as Record<string, unknown>;

  return (
    typeof candidate.id === "string" &&
    typeof candidate.name === "string" &&
    typeof candidate.price === "number" &&
    typeof candidate.in_stock === "boolean"
  );
}

function parseProducts(payload: unknown): Product[] {
  if (!Array.isArray(payload)) {
    return [];
  }

  return payload.filter(isValidProduct);
}

export async function sendChatMessage(
  payload: ChatRequest,
): Promise<ChatResponse> {
  const controller = new AbortController();
  const timeoutHandle = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(CHAT_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`Chat API error: ${response.status}`);
    }

    const rawData = (await response.json()) as Partial<ChatResponse>;

    if (
      typeof rawData.session_id !== "string" ||
      typeof rawData.message !== "string" ||
      typeof rawData.intent !== "string"
    ) {
      throw new Error("Chat API returned incomplete required fields");
    }

    return {
      session_id: rawData.session_id,
      message: rawData.message,
      intent: rawData.intent,
      products: parseProducts(rawData.products),
      metadata: rawData.metadata,
      error: rawData.error,
    };
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
    throw new Error("Chat request timed out. Please try again.");
    }

    throw error;
  } finally {
    clearTimeout(timeoutHandle);
  }
}
