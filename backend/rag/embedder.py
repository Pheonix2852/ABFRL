"""
Embedder module — loads MiniLM ONCE at module level.
Exposes a single embed() function for the rest of the app.
"""

from sentence_transformers import SentenceTransformer

# Load model ONCE at module level — never inside a function
# This avoids reloading the ~80MB model on every call
model = SentenceTransformer("all-MiniLM-L6-v2")


def embed(text: str) -> list:
    """
    Embed a single text string into a 384-dim vector.
    Returns a plain Python list (JSON-serializable).
    """
    return model.encode(text, normalize_embeddings=True).tolist()


def embed_batch(texts: list[str]) -> list[list]:
    """
    Embed a batch of text strings. More efficient than calling
    embed() in a loop because SentenceTransformer batches internally.
    """
    embeddings = model.encode(texts, normalize_embeddings=True)
    return [e.tolist() for e in embeddings]
