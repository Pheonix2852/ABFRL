import type { Product } from "@/types/product";
import type { ActiveQueryContext } from "@/store/activeQueryStore";

export function filterProductsByContext(
  products: Product[],
  context: ActiveQueryContext,
): { valid: Product[]; filtered: Product[] } {
  if (!context.gender && !context.category) {
    return { valid: products, filtered: [] };
  }

  const valid: Product[] = [];
  const filtered: Product[] = [];

  for (const product of products) {
    let ok = true;
    if (context.gender === "men" && product.gender_tags?.includes("women")) {
      ok = false;
    }
    if (context.gender === "women" && product.gender_tags?.includes("men")) {
      ok = false;
    }

    if (ok) {
      valid.push(product);
    } else {
      filtered.push(product);
    }
  }

  return { valid, filtered };
}
