import { StyleSheet, Text, View } from "react-native";

type ChatBubbleProps = {
  text: string;
  role: "user" | "assistant";
  timestamp?: string;
};

export function ChatBubble({ text, role, timestamp }: ChatBubbleProps) {
  const isUser = role === "user";

  return (
    <View style={[styles.row, isUser ? styles.rowUser : styles.rowAssistant]}>
      <View style={[styles.bubble, isUser ? styles.bubbleUser : styles.bubbleAssistant]}>
        <Text style={[styles.text, isUser ? styles.textUser : styles.textAssistant]}>{text}</Text>
        {timestamp ? (
          <Text style={[styles.timestamp, isUser ? styles.textUser : styles.textAssistant]}>
            {timestamp}
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
  timestamp: {
    marginTop: 6,
    fontSize: 10,
    opacity: 0.8,
  },
});
