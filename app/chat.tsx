import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useRouter } from "expo-router";

import { Header } from "@/components/layout/Header";
import { ScreenWrapper } from "@/components/layout/ScreenWrapper";
import { ChatBubble } from "@/components/ui/ChatBubble";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { buildAugmentedMessage, sendChatMessageWithRetry } from "@/services/chatApi";
import { useActiveQueryStore } from "@/store/activeQueryStore";
import { useChatStore } from "@/store/chatStore";
import { useOnboardingStore } from "@/store/onboardingStore";
import { useSessionStore } from "@/store/sessionStore";
import { useUserProfileStore } from "@/store/userProfileStore";
import { displayValue } from "@/utils/displayValue";
import { parseMessageSections } from "@/utils/messageParser";
import { extractQueryContext } from "@/utils/queryContextExtractor";

const QUICK_PROMPTS = ["Tell me more", "Different color", "Change budget"];

function createMessageId(): string {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function nowTimeLabel(): string {
  return new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function ChatScreen() {
  const router = useRouter();

  const sessionId = useSessionStore((state) => state.sessionId);
  const setSessionId = useSessionStore((state) => state.setSessionId);
  const resetSession = useSessionStore((state) => state.resetSession);

  const answers = useOnboardingStore((state) => state.answers);
  const initialPrompt = useOnboardingStore((state) => state.initialPrompt);
  const clearInitialPrompt = useOnboardingStore((state) => state.clearInitialPrompt);
  const clearOnboarding = useOnboardingStore((state) => state.clearAnswers);

  const messages = useChatStore((state) => state.messages);
  const addMessage = useChatStore((state) => state.addMessage);
  const clearChat = useChatStore((state) => state.clearChat);
  const setProducts = useChatStore((state) => state.setProducts);
  const products = useChatStore((state) => state.products);

  const profile = useUserProfileStore((state) => state.profile);
  const activeContext = useActiveQueryStore((state) => state.context);
  const setActiveContext = useActiveQueryStore((state) => state.setContext);

  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState("Waking up the style engine...");
  const [retryPayload, setRetryPayload] = useState<string | null>(null);

  const hasMessages = messages.length > 0;

  const handleSend = useCallback(async (message: string, appendUserMessage = false) => {
    const trimmed = message.trim();

    if (!trimmed) {
      return;
    }

    if (!profile) {
      setError("Profile not ready yet. Please try again.");
      return;
    }

    const extracted = extractQueryContext(trimmed);
    setActiveContext(extracted);
    const mergedContext = { ...activeContext, ...extracted };
    const finalMessage = buildAugmentedMessage(trimmed, mergedContext);

    if (appendUserMessage) {
      addMessage({
        id: createMessageId(),
        role: "user",
        text: trimmed,
        timestamp: nowTimeLabel(),
      });
    }

    setLoading(true);
    setError(null);
    setRetryPayload(trimmed);
    setLoadingMessage("Waking up the style engine...");

    try {
      const response = await sendChatMessageWithRetry(
        {
          message: finalMessage,
          user_id: profile.user_id,
          session_id: sessionId,
        },
        0,
        (attempt) => {
          if (attempt > 0) {
            setLoadingMessage("Still working on it...");
          }
        },
      );

      if (response.error) {
        throw new Error(response.error);
      }

      setSessionId(response.session_id);
      setProducts(response.products ?? []);

      addMessage({
        id: createMessageId(),
        role: "assistant",
        text: displayValue(response.message),
        timestamp: nowTimeLabel(),
      });
    } catch (chatError) {
      setError(chatError instanceof Error ? chatError.message : "Unable to send message");
    } finally {
      setLoading(false);
    }
  }, [
    activeContext,
    addMessage,
    profile,
    sessionId,
    setActiveContext,
    setProducts,
    setSessionId,
  ]);

  useEffect(() => {
    if (!answers && !hasMessages && !initialPrompt) {
      router.replace("/landing");
      return;
    }

    if (initialPrompt && !hasMessages && !loading) {
      void handleSend(initialPrompt, true);
      clearInitialPrompt();
    }
  }, [
    answers,
    clearInitialPrompt,
    handleSend,
    hasMessages,
    initialPrompt,
    loading,
    router,
  ]);

  const showSuggestions = useMemo(
    () => !loading && products.length === 0 && messages.some((item) => item.role === "assistant"),
    [loading, messages, products.length],
  );

  const onSendPress = () => {
    const draft = input;
    setInput("");
    void handleSend(draft, true);
  };

  const handleReset = () => {
    clearChat();
    clearOnboarding();
    resetSession();
    setError(null);
    setInput("");
    router.replace("/landing");
  };

  return (
    <ScreenWrapper padded={false}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <View style={styles.container}>
          <Header title="Stylist Chat" rightActionLabel="Reset" onRightAction={handleReset} />

          {error ? (
            <View style={styles.errorWrap}>
              <ErrorBanner
                message={error}
                onRetry={retryPayload ? () => void handleSend(retryPayload, false) : undefined}
              />
            </View>
          ) : null}

          <ScrollView style={styles.messages} contentContainerStyle={styles.messagesContent}>
            {messages.map((message) => (
              <ChatBubble
                key={message.id}
                role={message.role}
                text={message.text}
                sections={
                  message.role === "assistant"
                    ? parseMessageSections(message.text)
                    : undefined
                }
                onSuggestionSelect={(chip) => void handleSend(chip, true)}
                timestamp={message.timestamp}
              />
            ))}

            {loading ? (
              <View style={styles.loaderRow}>
                <ActivityIndicator color="#13293d" />
                <Text style={styles.loaderText}>{loadingMessage}</Text>
              </View>
            ) : null}

            {showSuggestions ? (
              <View style={styles.suggestionWrap}>
                {QUICK_PROMPTS.map((prompt) => (
                  <Pressable
                    key={prompt}
                    style={styles.suggestionChip}
                    onPress={() => void handleSend(prompt, true)}
                  >
                    <Text style={styles.suggestionText}>{prompt}</Text>
                  </Pressable>
                ))}
              </View>
            ) : null}

            {products.length > 0 ? (
              <Pressable
                onPress={() => router.push("/recommendations")}
                style={styles.recommendationsButton}
              >
                <Text style={styles.recommendationsButtonText}>View Recommendations</Text>
              </Pressable>
            ) : null}
          </ScrollView>

          <View style={styles.inputRow}>
            <TextInput
              placeholder="Type your message"
              placeholderTextColor="#8d949c"
              value={input}
              onChangeText={setInput}
              style={styles.input}
              editable={!loading}
            />
            <Pressable
              onPress={onSendPress}
              style={[styles.sendButton, loading && styles.sendButtonDisabled]}
              disabled={loading}
            >
              <Text style={styles.sendText}>Send</Text>
            </Pressable>
          </View>
        </View>
      </KeyboardAvoidingView>
    </ScreenWrapper>
  );
}

const styles = StyleSheet.create({
  flex: {
    flex: 1,
  },
  container: {
    flex: 1,
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 14,
    backgroundColor: "#f8f3eb",
  },
  errorWrap: {
    marginBottom: 10,
  },
  messages: {
    flex: 1,
  },
  messagesContent: {
    paddingBottom: 14,
  },
  loaderRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginTop: 6,
  },
  loaderText: {
    color: "#33414e",
    fontSize: 13,
    fontWeight: "600",
  },
  suggestionWrap: {
    marginTop: 14,
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  suggestionChip: {
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderWidth: 1,
    borderColor: "#dbc7ab",
    backgroundColor: "#f6eee2",
  },
  suggestionText: {
    fontSize: 12,
    color: "#3f4a56",
    fontWeight: "700",
  },
  recommendationsButton: {
    marginTop: 16,
    alignSelf: "flex-start",
    backgroundColor: "#d56a00",
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 999,
  },
  recommendationsButtonText: {
    color: "#fff",
    fontSize: 13,
    fontWeight: "800",
  },
  inputRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginTop: 10,
  },
  input: {
    flex: 1,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#ddd2c4",
    paddingHorizontal: 12,
    paddingVertical: 10,
    backgroundColor: "#fffdfa",
    color: "#1f2a34",
  },
  sendButton: {
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 10,
    backgroundColor: "#13293d",
  },
  sendButtonDisabled: {
    opacity: 0.45,
  },
  sendText: {
    color: "#f7f4ef",
    fontWeight: "700",
  },
});
