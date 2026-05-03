import { Image, Pressable, StyleSheet, Text, View } from "react-native";

import { displayValue } from "@/utils/displayValue";
import type { Product } from "@/types/product";

type ProductCardProps = {
  product: Product;
  onReserve: (id: string) => void;
  reserving?: boolean;
};

export function ProductCard({ product, onReserve, reserving = false }: ProductCardProps) {
  const disabled = !product.in_stock || reserving;
  const imageUrl = displayValue(product.image_url);
  const hasDiscount =
    typeof product.discounted_price === "number" &&
    product.discounted_price > 0 &&
    product.discounted_price < product.price;
  const savings = hasDiscount
    ? Math.max(0, Number(product.price) - Number(product.discounted_price))
    : 0;

  return (
    <View style={styles.card}>
      {imageUrl ? (
        <Image source={{ uri: imageUrl }} style={styles.image} resizeMode="cover" />
      ) : (
        <View style={[styles.image, styles.imageFallback]}>
          <Text style={styles.imageFallbackText}>No image</Text>
        </View>
      )}

      <View style={styles.body}>
        <View style={styles.topLine}>
          <Text style={styles.name}>{displayValue(product.name)}</Text>
          <View style={[styles.stockBadge, product.in_stock ? styles.inStock : styles.outStock]}>
            <Text style={[styles.stockText, product.in_stock ? styles.inStockText : styles.outStockText]}>
              {product.in_stock ? "In stock" : "Out of stock"}
            </Text>
          </View>
        </View>

        {product.availability_badge ? (
          <View style={styles.availabilityPill}>
            <Text style={styles.availabilityText}>{displayValue(product.availability_badge)}</Text>
          </View>
        ) : null}

        <View style={styles.priceLine}>
          {hasDiscount ? (
            <>
              <Text style={styles.price}>Rs. {displayValue(product.discounted_price)}</Text>
              <Text style={styles.originalPrice}>Rs. {displayValue(product.price)}</Text>
            </>
          ) : (
            <Text style={styles.price}>Rs. {displayValue(product.price)}</Text>
          )}
          {hasDiscount && savings > 0 ? (
            <Text style={styles.savingsBadge}>Save Rs. {displayValue(savings)}</Text>
          ) : null}
        </View>

        {product.why_for_you ? <Text style={styles.why}>Why for you: {displayValue(product.why_for_you)}</Text> : null}

        <Pressable
          onPress={() => onReserve(product.id)}
          disabled={disabled}
          style={({ pressed }) => [
            styles.reserveButton,
            disabled ? styles.reserveButtonDisabled : null,
            pressed && !disabled ? styles.reserveButtonPressed : null,
          ]}
        >
          <Text style={styles.reserveButtonText}>{reserving ? "Reserving..." : "Reserve"}</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#fffdfa",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#eadfcd",
    marginBottom: 12,
    overflow: "hidden",
  },
  image: {
    width: "100%",
    height: 180,
    backgroundColor: "#f2ece0",
  },
  imageFallback: {
    justifyContent: "center",
    alignItems: "center",
  },
  imageFallbackText: {
    color: "#7f7f7f",
    fontWeight: "600",
  },
  body: {
    padding: 12,
    gap: 8,
  },
  topLine: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 8,
  },
  name: {
    flex: 1,
    fontSize: 16,
    fontWeight: "700",
    color: "#13293d",
  },
  stockBadge: {
    borderRadius: 999,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  inStock: {
    backgroundColor: "#d7f7de",
  },
  outStock: {
    backgroundColor: "#fde4e4",
  },
  stockText: {
    fontSize: 11,
    fontWeight: "700",
  },
  inStockText: {
    color: "#1f6f34",
  },
  outStockText: {
    color: "#7c1f1f",
  },
  availabilityPill: {
    alignSelf: "flex-start",
    borderRadius: 999,
    paddingHorizontal: 8,
    paddingVertical: 3,
    backgroundColor: "#e7edf7",
  },
  availabilityText: {
    color: "#21354a",
    fontSize: 11,
    fontWeight: "700",
  },
  priceLine: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  price: {
    fontSize: 15,
    fontWeight: "800",
    color: "#0a7d4a",
  },
  originalPrice: {
    fontSize: 13,
    color: "#7f7f7f",
    textDecorationLine: "line-through",
  },
  savingsBadge: {
    marginLeft: "auto",
    borderRadius: 999,
    paddingHorizontal: 8,
    paddingVertical: 3,
    backgroundColor: "#e4f7ea",
    color: "#116b34",
    fontSize: 11,
    fontWeight: "800",
    overflow: "hidden",
  },
  why: {
    color: "#2b3440",
    fontSize: 13,
    lineHeight: 18,
  },
  reserveButton: {
    marginTop: 4,
    backgroundColor: "#d56a00",
    borderRadius: 12,
    paddingVertical: 10,
    alignItems: "center",
  },
  reserveButtonDisabled: {
    opacity: 0.45,
  },
  reserveButtonPressed: {
    opacity: 0.85,
  },
  reserveButtonText: {
    color: "#fff",
    fontSize: 14,
    fontWeight: "700",
  },
});
