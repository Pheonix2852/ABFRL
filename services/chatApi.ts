import { CHAT_ENDPOINT } from "@/constants/config";
import { useUserProfileStore } from "@/store/userProfileStore";
import type { ActiveQueryContext } from "@/store/activeQueryStore";
import type { ChatRequest, ChatResponse } from "@/types/chat";
import type { Product } from "@/types/product";

const REQUEST_TIMEOUT_MS = 45000;
const RETRY_DELAYS_MS = [0, 2000, 5000, 10000];
const CONTINUATION_TRIGGERS = ["more", "show more", "different", "cheaper", "another", "else"];

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

async function requestChat(payload: ChatRequest): Promise<ChatResponse> {
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
      const httpError = new Error(`Chat API error: ${response.status}`) as Error & {
        status?: number;
      };
      httpError.status = response.status;
      throw httpError;
    }

    const rawData = (await response.json()) as Partial<ChatResponse>;

    if (
      typeof rawData.session_id !== "string" ||
      typeof rawData.message !== "string" ||
      typeof rawData.intent !== "string"
    ) {
      throw new Error("Chat API returned incomplete required fields");
    }

    const data: ChatResponse = {
      session_id: rawData.session_id,
      message: rawData.message,
      intent: rawData.intent,
      products: parseProducts(rawData.products),
      metadata: rawData.metadata ?? null,
      error: rawData.error ?? null,
    };

    const { updateProfile } = useUserProfileStore.getState();
    if (data.metadata?.loyalty_tier) {
      updateProfile({ loyalty_tier: data.metadata.loyalty_tier });
    }

    return data;
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw new Error("Chat request timed out. Please try again.");
    }

    throw error;
  } finally {
    clearTimeout(timeoutHandle);
  }
}

export async function sendChatMessage(payload: ChatRequest): Promise<ChatResponse> {
  return requestChat(payload);
}

export async function sendChatMessageWithRetry(
  payload: ChatRequest,
  attempt = 0,
  onAttempt?: (attempt: number) => void,
): Promise<ChatResponse> {
  try {
    if (onAttempt) {
      onAttempt(attempt);
    }
    return await requestChat(payload);
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw new Error("Chat request timed out. Please try again.");
    }

    const status = (error as Error & { status?: number }).status;
    if (status && status >= 500 && attempt < RETRY_DELAYS_MS.length - 1) {
      await new Promise((resolve) => setTimeout(resolve, RETRY_DELAYS_MS[attempt]));
      return sendChatMessageWithRetry(payload, attempt + 1, onAttempt);
    }

    throw error;
  }
}

export function buildAugmentedMessage(
  userText: string,
  activeContext: ActiveQueryContext,
): string {
  const lower = userText.toLowerCase().trim();
  const isContinuation =
    CONTINUATION_TRIGGERS.some((trigger) => lower.includes(trigger)) &&
    lower.split(/\s+/).length <= 4;

  if (!isContinuation) {
    return userText;
  }

  const parts = [userText];
  if (activeContext.gender) {
    parts.push(`for ${activeContext.gender}`);
  }
  if (activeContext.category) {
    parts.push(`in ${String(activeContext.category).replace("_", " ")}`);
  }
  if (activeContext.budget_max) {
    parts.push(`under Rs.${activeContext.budget_max}`);
  }
  if (activeContext.occasion) {
    parts.push(`for ${activeContext.occasion}`);
  }

  return parts.join(" ");
}
