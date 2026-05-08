from __future__ import annotations

from typing import Any

from config import USE_NEW_TAXONOMY
from models.search_models import SearchPlan
from search.taxonomy import normalize_category, normalize_color
from services import taxonomy_service


def _unwrap_product(item: dict[str, Any]) -> dict[str, Any]:
    if isinstance(item.get("product"), dict):
        return item["product"]
    return item


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _price_from_product(product: dict[str, Any]) -> float:
    return _as_float(product.get("price"), 0.0)


def _family_match(product: dict[str, Any], plan: SearchPlan) -> float:
    requested = plan.subcategory
    if not requested:
        return 0.5

    product_subcategory = str(product.get("subcategory") or "").lower()
    product_name = str(product.get("name") or "").lower()

    if USE_NEW_TAXONOMY and taxonomy_service.is_family_match(product_subcategory, requested):
        return 1.0

    normalized_requested = str(requested).lower()
    if normalized_requested in product_subcategory:
        return 1.0
    if normalized_requested in product_name:
        return 0.8

    if plan.category:
        product_category = normalize_category(product.get("subcategory") or product.get("category"))
        if product_category == plan.category:
            return 0.6

    return 0.0


def _budget_fit(product: dict[str, Any], plan: SearchPlan) -> float:
    price = _price_from_product(product)
    lower = plan.budget_min
    upper = plan.budget_max

    if lower is None and upper is None:
        return 0.5

    if lower is not None and upper is not None:
        if lower <= price <= upper:
            return 1.0
        span = max(upper - lower, 1)
        distance = min(abs(price - lower), abs(price - upper))
        return max(0.0, 1.0 - (distance / span))

    if upper is not None:
        if price <= upper:
            return 1.0
        return max(0.0, 1.0 - ((price - upper) / max(upper, 1)))

    if price >= lower:
        return 1.0
    return max(0.0, price / max(lower, 1))


def _color_match(product: dict[str, Any], plan: SearchPlan) -> float:
    if not plan.colors:
        return 0.5

    normalized_product_colors = product.get("normalized_colors") or []
    product_colors = [str(color).lower() for color in normalized_product_colors or product.get("colors") or []]
    name = str(product.get("name") or "").lower()
    normalized_plan_colors = [normalize_color(color) or color.lower() for color in plan.colors]

    for color in normalized_plan_colors:
        if any(color in candidate or candidate in color for candidate in product_colors):
            return 1.0
        if color in name:
            return 0.9
    return 0.0


def _occasion_match(product: dict[str, Any], plan: SearchPlan) -> float:
    if not plan.occasion:
        return 0.5

    product_occasions = [str(tag).lower() for tag in product.get("occasionTags") or product.get("occasion_tags") or []]
    name = str(product.get("name") or "").lower()
    if plan.occasion.lower() in product_occasions:
        return 1.0
    if plan.occasion.lower() in name:
        return 0.8
    return 0.0


def _rating(product: dict[str, Any]) -> float:
    rating = _as_float(product.get("rating"), 0.0)
    return max(0.0, min(rating / 5.0, 1.0))


def rank_products(products: list[dict[str, Any]], plan: SearchPlan) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []

    for item in products:
        product = _unwrap_product(item)
        semantic_similarity = _as_float(item.get("semantic_similarity", item.get("score", item.get("retrieval_score", 0.0))))
        family_match = _family_match(product, plan)
        budget_fit = _budget_fit(product, plan)
        color_match = _color_match(product, plan)
        occasion_match = _occasion_match(product, plan)
        rating = _rating(product)

        score = (
            0.45 * family_match
            + 0.20 * semantic_similarity
            + 0.15 * budget_fit
            + 0.10 * color_match
            + 0.05 * occasion_match
            + 0.05 * rating
        )

        ranked.append(
            {
                **item,
                "product": product,
                "rank_score": score,
                "semantic_similarity": semantic_similarity,
                "family_match": family_match,
                "budget_fit": budget_fit,
                "color_match": color_match,
                "occasion_match": occasion_match,
                "rating_score": rating,
            }
        )

    ranked.sort(key=lambda item: item.get("rank_score", 0.0), reverse=True)
    return ranked
