import { ScrollView, StyleSheet, Text, TouchableOpacity } from "react-native";

import { displayValue } from "@/utils/displayValue";

interface SuggestionChipsProps {
  chips: string[];
  onSelect: (chip: string) => void;
}

export function SuggestionChips({ chips, onSelect }: SuggestionChipsProps) {
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.container}
    >
      {chips.map((chip) => {
        const chipText = displayValue(chip);

        return (
          <TouchableOpacity key={chipText} style={styles.chip} onPress={() => onSelect(chipText)}>
            <Text style={styles.chipText}>{chipText}</Text>
          </TouchableOpacity>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: 8,
    paddingVertical: 6,
  },
  chip: {
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderWidth: 1,
    borderColor: "#dbc7ab",
    backgroundColor: "#f6eee2",
  },
  chipText: {
    fontSize: 12,
    color: "#3f4a56",
    fontWeight: "700",
  },
});
