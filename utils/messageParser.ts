import { displayValue } from "@/utils/displayValue";

export type MessageSection =
  | { type: "greeting"; text: string }
  | { type: "summary"; text: string }
  | { type: "suggestion_chips"; chips: string[] }
  | { type: "error_explanation"; text: string }
  | { type: "plain"; text: string };

export function parseMessageSections(raw: unknown): MessageSection[] {
  const normalizedRaw = displayValue(raw);

  if (!normalizedRaw) {
    return [{ type: "plain", text: "" }];
  }

  const lines = normalizedRaw
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  const suggestionLines = lines.filter((line) => line.startsWith("- "));
  if (suggestionLines.length > 0) {
    return [
      {
        type: "suggestion_chips",
        chips: suggestionLines.map((line) => line.slice(2)),
      },
    ];
  }

  const sections: MessageSection[] = [];
  for (const line of lines) {
    if (/^(hey|hi|hello) [a-z]/i.test(line) && sections.length === 0) {
      sections.push({ type: "greeting", text: line });
      continue;
    }

    sections.push({ type: "plain", text: line });
  }

  return sections.length > 0 ? sections : [{ type: "plain", text: normalizedRaw }];
}
