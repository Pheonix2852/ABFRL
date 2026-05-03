"""
NLU Agent — Natural Language Understanding
Extracts intent + entities from raw user message using Groq (Llama 3.1 8B).
"""

import os
import json
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SUBCATEGORY_NORMALIZER = {
    "pant": "pants",
    "pants": "pants",
    "trouser": "pants",
    "trousers": "pants",
    "slacks": "pants",
    "bottoms": "pants",

    "shirt": "shirt",
    "shirts": "shirt",
    "formal shirt": "shirt",

    "tshirt": "tshirt",
    "tee": "tshirt",
    "t-shirt": "tshirt",

    "short": "shorts",
    "shorts": "shorts",

    "shoe": "shoes",
    "shoes": "shoes",
    "footwear": "shoes",
    "sneaker": "shoes",
    "sneakers": "shoes",
    "loafer": "shoes",
    "loafers": "shoes",
    "heels": "shoes",
    "sandal": "shoes",
    "sandals": "shoes",

    "jewellery": "jewellery",
    "jewelry": "jewellery",
    "necklace": "jewellery",
    "earrings": "jewellery",

    "purse": "bags",
    "bag": "bags",
    "handbag": "bags",

    "kurti": "kurta",
    "kurta": "kurta",

    "denim": "jeans",
    "jean": "jeans",

    "saree": "saree",
    "sarees": "saree",
    "sari": "saree",
}


def _sanitize_nullable(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.lower() in {"null", "none", "nil", "na", "n/a"}:
        return None
    return value


def _has_inventory_cue(message: str, entities: dict) -> bool:
    lower = message.lower()
    if entities.get("sku_id"):
        return True
    return any(
        token in lower
        for token in [
            "stock",
            "available",
            "availability",
            "inventory",
            "in stock",
            "out of stock",
            "sku",
            "quantity",
            "how many",
            "left",
            "remaining",
        ]
    )

SYSTEM_PROMPT = """You are the NLU (Natural Language Understanding) module for a retail fashion AI assistant for ABFRL (Aditya Birla Fashion & Retail Limited).

Your ONLY job is to extract structured intent and entities from the user's message.

VALID INTENTS (pick exactly one):
- "recommendation"   → user wants product suggestions (e.g. "show me red kurtas for Diwali")
- "inventory_check"  → user asks about stock/availability (e.g. "is SKU_004 available?")
- "loyalty_check"    → user asks about their loyalty tier, points, or discounts
- "greeting"         → user says hello, hi, hey, etc.
- "fallback"         → anything you cannot classify

ENTITY FIELDS to extract (set null if not mentioned):
- category: one of "ethnic_wear", "western_wear", "accessories", "footwear", or null
- subcategory: e.g. "saree", "kurta", "lehenga", "sherwani", "salwar_suit", "dress", "jeans", "top", "blazer", "handbag", "jewellery", "scarf", "belt", "heels", "ethnic_footwear", "sneakers", or null
- color: the color mentioned, or null
- budget_min: minimum price as integer, or null
- budget_max: maximum price as integer, or null
- occasion: one of "wedding", "festive", "party", "casual", "office", "traditional", or null
- size: e.g. "S", "M", "L", "XL", "XS", "One Size", or shoe sizes "5"-"9", or null
- sku_id: e.g. "SKU_004" if user mentions a specific product, or null
- store: one of "online_warehouse", "store_mumbai", "store_delhi", "store_bangalore", or null
- gender: one of "men", "women", "unisex", or null — extract ONLY from explicit cues; do NOT guess

You MUST return ONLY valid JSON in this exact format:
{
  "intent": "<intent>",
  "entities": {
    "category": null,
    "subcategory": null,
    "color": null,
    "budget_min": null,
    "budget_max": null,
    "occasion": null,
    "size": null,
    "sku_id": null,
    "store": null,
    "gender": null
  }
}

IMPORTANT RULES:
1. Return ONLY the JSON — no markdown, no explanation, no extra text.
2. If the user mentions "kurta", "saree", "lehenga", "sherwani" → category is "ethnic_wear".
3. If the user mentions "dress", "jeans", "top", "blazer" → category is "western_wear".
4. If the user mentions "bag", "necklace", "earrings", "belt", "scarf" → category is "accessories".
5. If the user mentions "shoes", "heels", "sneakers", "sandals", "juttis", "chappals" → category is "footwear".
6. "under 2000", "below 2000", "within 2000" → budget_max = 2000.
7. "Diwali", "festive season", "puja" → occasion = "festive".
8. "wedding", "shaadi", "reception" → occasion = "wedding".
9. Gender extraction rules (set null if no clear cue):
   - "ladies", "women's", "female", "girl", "wife", "girlfriend" → gender = "women"
   - "men's", "gents", "male", "boy", "boyfriend", "husband" → gender = "men"
   - Product explicitly described as unisex → gender = "unisex"
   - No gender cue present → gender = null (do NOT guess)
10. Budget range rules:
    - "between 1000 and 3000" → budget_min = 1000, budget_max = 3000
    - "above 500", "more than 500", "at least 500" → budget_min = 500, budget_max = null
    - "under 2000", "below 2000", "within 2000" → budget_min = null, budget_max = 2000
11. If the message is 3 words or fewer AND contains "more", "different", "cheaper",
    "another", or "else" → intent is "recommendation" and assume missing entities
    can be inherited from prior context.
"""


def run(message: str, context: str = "") -> dict:
    """
    Parse a user message into structured intent + entities.

    Args:
        message: Raw user message from the current turn.
        context: Optional formatted string of recent conversation turns
                 (built by orchestrator.build_conversation_context).
                 When provided, it is prepended to the message so the
                 model can resolve references across turns.

    Returns:
        dict with 'intent' and 'entities' keys.
    """
    # Prepend conversation context so the LLM can resolve cross-turn references
    full_message = f"{context}\n\nCurrent message: {message}" if context else message
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": full_message},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        result = json.loads(response.choices[0].message.content)

        entities = result.get("entities", {})
        if not isinstance(entities, dict):
            entities = {}

        for key in list(entities.keys()):
            entities[key] = _sanitize_nullable(entities.get(key))

        raw = entities.get("subcategory")
        if raw:
            entities["subcategory"] = SUBCATEGORY_NORMALIZER.get(
                str(raw).lower(),
                str(raw).lower()
            )

        # DO NOT set default gender — let null mean unisex/ambiguous

        result["entities"] = entities

        intent = result.get("intent", "fallback")
        msg = message.lower().strip()

        # continuation commands
        if msg in ["more", "tell me more", "another", "different color", "cheaper"]:
            result["intent"] = "recommendation"

        # browsing requests should never become inventory checks
        if (
            result["intent"] == "inventory_check"
            and not _has_inventory_cue(message, entities)
        ):
            result["intent"] = "recommendation"

        # Ensure required keys exist
        if "intent" not in result:
            result["intent"] = "fallback"
        if "entities" not in result:
            result["entities"] = {}

        return result

    except Exception as e:
        print(f"[nlu_agent] Error: {e}")
        return {
            "intent": "fallback",
            "entities": {},
            "error": str(e),
        }
