import type { ActiveQueryContext } from "@/store/activeQueryStore";

export function extractQueryContext(message: string): Partial<ActiveQueryContext> {
  const lower = message.toLowerCase();
  const context: Partial<ActiveQueryContext> = {};

  if (/\b(men|men's|gents?|male|boy|husband)\b/.test(lower)) {
    context.gender = "men";
  } else if (/\b(women|women's|ladies|female|girl|wife|girlfriend)\b/.test(lower)) {
    context.gender = "women";
  }

  if (/\b(saree|sherwani|kurta|lehenga|salwar|anarkali)\b/.test(lower)) {
    context.category = "ethnic_wear";
  } else if (/\b(dress|jeans|top|blazer|western)\b/.test(lower)) {
    context.category = "western_wear";
  } else if (/\b(bag|handbag|jewellery|scarf|earrings|necklace)\b/.test(lower)) {
    context.category = "accessories";
  } else if (/\b(shoes|heels|sneakers|sandals|juttis)\b/.test(lower)) {
    context.category = "footwear";
  }

  const budgetMatch = lower.match(/under (\d+)|below (\d+)|within (\d+)/);
  if (budgetMatch) {
    context.budget_max = parseInt(budgetMatch[1] || budgetMatch[2] || budgetMatch[3], 10);
  }

  if (/\b(diwali|festive|puja|eid)\b/.test(lower)) {
    context.occasion = "festive";
  } else if (/\b(wedding|shaadi|reception)\b/.test(lower)) {
    context.occasion = "wedding";
  } else if (/\b(party|celebration)\b/.test(lower)) {
    context.occasion = "party";
  } else if (/\b(office|work|formal)\b/.test(lower)) {
    context.occasion = "office";
  }

  return context;
}
