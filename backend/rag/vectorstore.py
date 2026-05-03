"""
Qdrant Cloud vector store wrapper.
Collection: abfrl_products | Vector size: 384 | Distance: Cosine
"""

import os
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
    Range,
    PayloadSchemaType,
)

COLLECTION_NAME = "abfrl_products"
VECTOR_SIZE = 384


def get_client() -> QdrantClient:
    """Create and return a Qdrant Cloud client."""
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")

    if not url or not api_key:
        raise ValueError(
            "QDRANT_URL and QDRANT_API_KEY must be set in environment variables. "
            "See .env.example for the template."
        )

    return QdrantClient(url=url, api_key=api_key)


def delete_collection(client: QdrantClient) -> None:
    """Delete the collection if it exists."""
    collections = client.get_collections().collections
    existing_names = [c.name for c in collections]
    if COLLECTION_NAME in existing_names:
        client.delete_collection(COLLECTION_NAME)
        print(f"[vectorstore] Deleted collection '{COLLECTION_NAME}'")


def ensure_payload_indexes(client: QdrantClient) -> None:
    """
    Create payload indexes for filterable fields if they don't already exist.

    Indexes created:
        - gender_tags  → KEYWORD
        - category     → KEYWORD
        - in_stock     → BOOL
        - price        → FLOAT
    """
    field_schema_map = {
    "gender_tags": PayloadSchemaType.KEYWORD,
    "category": PayloadSchemaType.KEYWORD,
    "subcategory": PayloadSchemaType.KEYWORD,
    "colors": PayloadSchemaType.KEYWORD,
    "in_stock": PayloadSchemaType.BOOL,
    "price": PayloadSchemaType.FLOAT,
    "occasionTags": PayloadSchemaType.KEYWORD,
    "brand": PayloadSchemaType.KEYWORD
}

    # Fetch already-indexed fields to avoid redundant API calls
    collection_info = client.get_collection(COLLECTION_NAME)
    existing_indexes = set(collection_info.payload_schema.keys())

    for field, schema_type in field_schema_map.items():
        if field not in existing_indexes:
            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name=field,
                field_schema=schema_type,
            )
            print(f"[vectorstore] Created payload index: '{field}' ({schema_type.name})")
        else:
            print(f"[vectorstore] Payload index already exists: '{field}'")


def ensure_collection(client: QdrantClient) -> None:
    """Create the collection if it doesn't exist, then ensure payload indexes."""
    collections = client.get_collections().collections
    existing_names = [c.name for c in collections]

    if COLLECTION_NAME not in existing_names:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE,
            ),
        )
        print(f"[vectorstore] Created collection '{COLLECTION_NAME}'")
    else:
        print(f"[vectorstore] Collection '{COLLECTION_NAME}' already exists")

    ensure_payload_indexes(client)


def collection_has_points(client: QdrantClient) -> bool:
    """Check if the collection already has data points."""
    try:
        info = client.get_collection(COLLECTION_NAME)
        return info.points_count > 0
    except Exception:
        return False


def upsert_points(
    client: QdrantClient,
    ids: list[int],
    vectors: list[list],
    payloads: list[dict],
) -> None:
    """Upsert a batch of points into the collection."""
    points = [
        PointStruct(id=id_, vector=vec, payload=payload)
        for id_, vec, payload in zip(ids, vectors, payloads)
    ]
    client.upsert(collection_name=COLLECTION_NAME, points=points)
    print(f"[vectorstore] Upserted {len(points)} points")


def search(
    client: QdrantClient,
    query_vector: list,
    top_k: int = 10,
    query_filter: Filter | None = None,
) -> list:
    """
    Search the collection for the closest vectors.

    Args:
        client:       Qdrant client instance.
        query_vector: Embedded query vector.
        top_k:        Maximum number of results to return.
        query_filter: Optional Qdrant Filter for deterministic pre-filtering
                      (e.g. gender, category, price range, in_stock).

    Returns:
        List of ScoredPoint objects with .payload and .score.
    """
    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        query_filter=query_filter,
        limit=top_k,
    )
    return results
