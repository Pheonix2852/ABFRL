from __future__ import annotations

import json
import os
import re
from difflib import SequenceMatcher
from typing import Any

_DATA_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "products.json")
)


def _load_products() -> dict[str, dict[str, Any]]:
    with open(_DATA_PATH, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
        return raw if isinstance(raw, dict) else {}


def _normalize(text: str | None) -> str:
    if text is None:
        return ""
    lowered = str(text).lower().strip()
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def resolve_product(query: str, subcategory: str | None = None) -> dict | None:
    products = _load_products()
    if not products:
        return None

    normalized_query = _normalize(query)
    normalized_subcategory = _normalize(subcategory)

    # 1) Direct SKU mention in query.
    sku_match = re.search(r"\bSKU_\d+\b", query.upper())
    if sku_match:
        sku_id = sku_match.group(0)
        product = products.get(sku_id)
        if product:
            return {
                "sku_id": sku_id,
                "product": product,
                "match_score": 1.0,
                "match_type": "sku",
            }

    best: dict | None = None
    for sku_id, product in products.items():
        name = _normalize(product.get("name"))
        family = _normalize(product.get("subcategory"))

        score = 0.0
        match_type = "fuzzy"

        if normalized_query and name and normalized_query in name:
            score = 0.98
            match_type = "name_contains"
        elif normalized_query and name and name in normalized_query:
            score = 0.95
            match_type = "name_contains"
        else:
            score = _similarity(normalized_query, name)
            if normalized_subcategory and normalized_subcategory == family:
                score += 0.15
                match_type = "subcategory+fuzzy"
            elif normalized_subcategory and normalized_subcategory in family:
                score += 0.1
                match_type = "subcategory+fuzzy"

        if best is None or score > best["match_score"]:
            best = {
                "sku_id": sku_id,
                "product": product,
                "match_score": score,
                "match_type": match_type,
            }

    if not best:
        return None

    threshold = 0.55
    if normalized_subcategory and best["match_score"] >= 0.45:
        threshold = 0.45

    if best["match_score"] < threshold:
        return None

    return best
