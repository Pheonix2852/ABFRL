export function displayValue(value: unknown): string {
  if (value == null) {
    return "";
  }

  if (typeof value === "string") {
    return value;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  if (Array.isArray(value)) {
    if (value.every((item) => typeof item === "string")) {
      return value.join(", ");
    }

    return value.map((item) => displayValue(item)).filter(Boolean).join(", ");
  }

  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    const textValue = record.text ?? record.message;

    if (typeof textValue === "string" || typeof textValue === "number") {
      return String(textValue);
    }

    try {
      return JSON.stringify(value);
    } catch {
      return "";
    }
  }

  return String(value);
}