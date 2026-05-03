"""
One-time product indexer.
Reads products.json → embeds each product → upserts to Qdrant Cloud.
CRITICAL: Always recreates the collection to ensure a fresh index.
"""

import json
import os

from rag.embedder import embed_batch
from rag import vectorstore


DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "products.json")


def _build_embed_text(product: dict) -> str:
    """
    Build the text string to embed for a product.
    Combines name, description, and occasion tags for rich semantic search.
    """
    occasion_tags = " ".join(product.get("occasionTags", []))
    colors = " ".join(product.get("colors", []))
    return (
        f"{product['name']} {product['description']} "
        f"{occasion_tags} {colors} {product.get('category', '')} "
        f"{product.get('subcategory', '')}"
    )


def run() -> None:
    """
    Index all products into Qdrant Cloud.
    Deletes existing collection and recreates it.
    """
    print("[indexer] Starting product indexing process...")

    # Connect to Qdrant Cloud
    client = vectorstore.get_client()
    
    print("[indexer] Deleting existing collection...")
    vectorstore.delete_collection(client)
    print("[indexer] Creating new collection...")
    vectorstore.ensure_collection(client)

    # Load products
    abs_path = os.path.abspath(DATA_PATH)
    print(f"[indexer] Loading products from {abs_path}")

    with open(abs_path, "r", encoding="utf-8") as f:
        products = json.load(f)

    if isinstance(products, dict):
        products = list(products.values())

    total = len(products)
    print(f"[indexer] Found {total} products to index")

    # Build texts and embed in batch
    print("[indexer] Generating embeddings...")
    texts = [_build_embed_text(p) for p in products]
    vectors = embed_batch(texts)
    print(f"[indexer] Generated {len(vectors)} embeddings")

    # Prepare IDs and payloads
    print("[indexer] Preparing payloads...")
    ids = list(range(1, total + 1))
    payloads = []
    for i, product in enumerate(products, start=1):
        print(f"[indexer] Indexing product {i} of {total}: {product['name']}")
        payloads.append({
            "id": product["id"],
            "name": product["name"],
            "category": product["category"],
            "subcategory": product.get("subcategory", ""),
            "price": product["price"],
            "sizes": product.get("sizes", []),
            "colors": product.get("colors", []),
            "occasionTags": product.get("occasionTags", []),
            "description": product["description"],
            "rating": product.get("rating", 0),
            "imageUrl": product.get("imageUrl", ""),
            "brand": product.get("brand", "ABFRL"),
            "gender_tags": product.get("gender_tags", []),
            "in_stock": product.get("in_stock", True),
        })

    # Upsert all at once
    print("[indexer] Upserting points to Qdrant...")
    vectorstore.upsert_points(client, ids, vectors, payloads)
    print(f"[indexer] Done. {total} products indexed successfully.")
