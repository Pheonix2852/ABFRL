import { StyleSheet, Text, View } from "react-native";

import { SuggestionChips } from "@/components/ui/SuggestionChips";
import { displayValue } from "@/utils/displayValue";
import type { MessageSection } from "@/utils/messageParser";

type ChatBubbleProps = {
  text: string;
  role: "user" | "assistant";
  timestamp?: string;
  sections?: MessageSection[];
  onSuggestionSelect?: (chip: string) => void;
};

export function ChatBubble({
  text,
  role,
  timestamp,
  sections,
  onSuggestionSelect,
}: ChatBubbleProps) {
  const isUser = role === "user";
  const resolvedSections = sections ?? [{ type: "plain", text }];

  return (
    <View style={[styles.row, isUser ? styles.rowUser : styles.rowAssistant]}>
      <View style={[styles.bubble, isUser ? styles.bubbleUser : styles.bubbleAssistant]}>
        {resolvedSections.map((section, index) => {
          if (section.type === "suggestion_chips") {
            return (
              <SuggestionChips
                key={`chips-${index}`}
                chips={section.chips}
                onSelect={(chip) => onSuggestionSelect?.(chip)}
              />
            );
          }

          const isGreeting = section.type === "greeting";
          return (
            <Text
              key={`${section.type}-${index}`}
              style={[
                styles.text,
                isUser ? styles.textUser : styles.textAssistant,
                isGreeting ? styles.greetingText : null,
              ]}
            >
              {displayValue(section.text)}
            </Text>
          );
        })}
        {timestamp ? (
          <Text style={[styles.timestamp, isUser ? styles.textUser : styles.textAssistant]}>
            {displayValue(timestamp)}
          </Text>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    marginBottom: 10,
    flexDirection: "row",
  },
  rowUser: {
    justifyContent: "flex-end",
  },
  rowAssistant: {
    justifyContent: "flex-start",
  },
  bubble: {
    maxWidth: "84%",
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  bubbleUser: {
    backgroundColor: "#13293d",
    borderBottomRightRadius: 6,
  },
  bubbleAssistant: {
    backgroundColor: "#efe8dc",
    borderBottomLeftRadius: 6,
  },
  text: {
    fontSize: 14,
    lineHeight: 20,
  },
  textUser: {
    color: "#f8f3eb",
  },
  textAssistant: {
    color: "#1e2329",
  },
  greetingText: {
    fontSize: 16,
    fontWeight: "700",
    color: "#2f3b46",
  },
  timestamp: {
    marginTop: 6,
    fontSize: 10,
    opacity: 0.8,
  },
});
