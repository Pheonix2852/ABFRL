from __future__ import annotations

import logging
from typing import Any

from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue, Range

from config import USE_NEW_TAXONOMY
from models.search_models import SearchPlan
from rag import vectorstore
from rag.embedder import embed
from services import taxonomy_service

logger = logging.getLogger(__name__)


SUBCATEGORY_ALIAS_EXPANSION = {
    "kurta": ["kurta"],
    "kurtas": ["kurta"],
    "pants": ["pants", "trousers", "jeans", "chinos", "joggers"],
    "trousers": ["pants", "trousers", "jeans", "chinos", "joggers"],
    "jeans": ["jeans"],
    "denim": ["jeans"],
    "shirts": ["shirt", "shirts", "formal_shirt", "casual_shirt"],
    "shirt": ["shirt", "shirts", "formal_shirt", "casual_shirt"],
    "shorts": ["shorts"],
    "shoe": ["sneakers", "loafers", "heels", "sandals", "flats", "ethnic_footwear"],
    "shoes": ["sneakers", "loafers", "heels", "sandals", "flats", "ethnic_footwear"],
    "sneakers": ["sneakers", "loafers", "heels", "sandals", "flats", "ethnic_footwear"],
    "loafers": ["sneakers", "loafers", "heels", "sandals", "flats", "ethnic_footwear"],
    "sandals": ["sneakers", "loafers", "heels", "sandals", "flats", "ethnic_footwear"],
    "footwear": ["sneakers", "loafers", "heels", "sandals", "flats", "ethnic_footwear"],
    "jewellery": ["jewellery"],
    "jewelry": ["jewellery"],
    "bags": ["handbag", "backpack", "wallet"],
    "bag": ["handbag", "backpack", "wallet"],
    "saree": ["saree", "sarees"],
    "sarees": ["saree", "sarees"],
    "dress": ["dress", "dresses"],
}


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _build_query_text(plan: SearchPlan) -> str:
    parts = [plan.intent or "recommendation"]
    if plan.category:
        parts.append(plan.category)
    if plan.subcategory:
        parts.append(plan.subcategory)
    if plan.gender:
        parts.append(plan.gender)
    if plan.colors:
        parts.extend(plan.colors)
    if plan.occasion:
        parts.append(plan.occasion)
    if plan.style:
        parts.append(plan.style)
    if plan.budget_max is not None:
        parts.append(f"under {plan.budget_max}")
    if plan.budget_min is not None:
        parts.append(f"above {plan.budget_min}")
    return " ".join(part for part in parts if part).strip()


def _build_filter(plan: SearchPlan) -> Filter:
    must = []

    # Filter by high-level category field (e.g., "ethnic_wear", "western_wear")
    if plan.category:
        must.append(FieldCondition(key="category", match=MatchValue(value=plan.category)))

    # Filter by product subcategory field (e.g., "kurta", "pants") with alias expansion
    if plan.subcategory:
        if USE_NEW_TAXONOMY:
            expanded = taxonomy_service.expand_aliases(plan.subcategory)
        else:
            expanded = SUBCATEGORY_ALIAS_EXPANSION.get(plan.subcategory.lower(), [plan.subcategory])
        if expanded:
            must.append(FieldCondition(key="subcategory", match=MatchAny(any=expanded)))
        else:
            must.append(FieldCondition(key="subcategory", match=MatchValue(value=plan.subcategory)))

    # Only apply gender filter if explicitly specified (no default)
    if plan.gender == "men":
        must.append(FieldCondition(key="gender_tags", match=MatchAny(any=["men", "unisex"])))
    elif plan.gender == "women":
        must.append(FieldCondition(key="gender_tags", match=MatchAny(any=["women", "unisex"])))
    # If gender is None, match all gender_tags (unisex, men, women)

    if plan.budget_max is not None:
        must.append(FieldCondition(key="price", range=Range(lte=plan.budget_max)))
    if plan.budget_min is not None:
        must.append(FieldCondition(key="price", range=Range(gte=plan.budget_min)))
    return Filter(must=must)


def _lexical_bonus(product: dict[str, Any], plan: SearchPlan) -> float:
    name = _safe_text(product.get("name")).lower()
    subcategory = _safe_text(product.get("subcategory")).lower()
    tokens = []
    if plan.category:
        tokens.append(plan.category.lower())
    if plan.subcategory:
        tokens.append(plan.subcategory.lower())
    if plan.colors:
        tokens.extend(color.lower() for color in plan.colors)
    if plan.occasion:
        tokens.append(plan.occasion.lower())
    bonus = 0.0
    for token in tokens:
        if token and (token in name or token in subcategory):
            bonus += 0.05
    return min(bonus, 0.2)


def _is_explicit_apparel_query(plan: SearchPlan) -> bool:
    return bool(_safe_text(plan.subcategory))


def _subcategory_match_score(product: dict[str, Any], plan: SearchPlan) -> float:
    requested = _safe_text(plan.subcategory).lower()
    if not requested:
        return 0.0

    product_subcategory = _safe_text(product.get("subcategory")).lower()
    if USE_NEW_TAXONOMY:
        return 1.0 if taxonomy_service.is_family_match(product_subcategory, requested) else 0.0

    allowed = {item.lower() for item in SUBCATEGORY_ALIAS_EXPANSION.get(requested, [requested])}
    return 1.0 if product_subcategory in allowed else 0.0


def _category_match_score(product: dict[str, Any], plan: SearchPlan) -> float:
    requested = _safe_text(plan.category).lower()
    if not requested:
        return 0.0
    return 1.0 if _safe_text(product.get("category")).lower() == requested else 0.0


def _compute_retrieval_score(product: dict[str, Any], semantic_similarity: float, lexical_bonus: float, plan: SearchPlan) -> float:
    category_score = _category_match_score(product, plan)
    subcategory_score = _subcategory_match_score(product, plan)
    explicit_query = _is_explicit_apparel_query(plan)

    # Query-type aware scoring:
    # - explicit apparel queries prioritize category/subcategory correctness over pure semantics
    # - vague queries keep semantic matching as dominant signal
    if explicit_query:
        score = (
            semantic_similarity * 0.35
            + lexical_bonus * 0.15
            + category_score * 0.40
            + subcategory_score * 0.90
        )
        # Strongly demote unrelated product types for explicit requests.
        if subcategory_score == 0.0:
            score -= 1.25
    else:
        score = (
            semantic_similarity * 0.80
            + lexical_bonus * 0.10
            + category_score * 0.10
        )

    return score


def retrieve_candidates(plan: SearchPlan, limit: int = 30) -> list[dict[str, Any]]:
    try:
        query_text = _build_query_text(plan)
        logger.info("[search.retrieval] query=%s", query_text)
        query_vector = embed(query_text or plan.intent or "fashion")

        client = vectorstore.get_client()
        query_filter = _build_filter(plan)
        logger.info("[search.retrieval] filter=%s", query_filter)
        
        results = vectorstore.search(
            client,
            query_vector,
            top_k=max(limit * 2, 30),
            query_filter=query_filter,
        )
        used_category_fallback = False

        candidates_before = len(results)
        logger.info("[search.retrieval] candidates_before_lexical=%d", candidates_before)
        explicit_query = _is_explicit_apparel_query(plan)

        if candidates_before == 0 and (plan.category or plan.subcategory):
            logger.info(
                "[search.retrieval] Zero exact matches (category=%s, subcategory=%s). Falling back.",
                plan.category,
                plan.subcategory,
            )
            fallback_plan = SearchPlan(
                intent=plan.intent,
                category=plan.category,
                subcategory=None,
                gender=plan.gender,
                budget_min=plan.budget_min,
                budget_max=plan.budget_max,
                colors=plan.colors,
                occasion=plan.occasion,
                style=plan.style,
                hard_constraints=plan.hard_constraints,
                soft_preferences=plan.soft_preferences,
                confidence=plan.confidence,
            )
            fallback_filter = _build_filter(fallback_plan)
            fallback_query_text = _build_query_text(fallback_plan)
            logger.info("[search.retrieval] fallback_filter=%s", fallback_filter)
            results = vectorstore.search(
                client,
                embed(fallback_query_text or query_text or plan.intent or "fashion"),
                top_k=max(limit * 2, 30),
                query_filter=fallback_filter,
            )
            used_category_fallback = True
            candidates_before = len(results)
            logger.info("[search.retrieval] candidates_after_fallback=%d", candidates_before)

        candidates: list[dict[str, Any]] = []
        for result in results:
            product = result.payload or {}
            semantic_similarity = float(result.score or 0.0)
            lexical_bonus = _lexical_bonus(product, plan)
            retrieval_score = _compute_retrieval_score(product, semantic_similarity, lexical_bonus, plan)
            candidates.append(
                {
                    "product": product,
                    "semantic_similarity": semantic_similarity,
                    "lexical_bonus": lexical_bonus,
                    "retrieval_score": retrieval_score,
                    "used_category_fallback": used_category_fallback,
                }
            )

        candidates.sort(key=lambda item: item.get("retrieval_score", 0.0), reverse=True)
        final_candidates = candidates[:limit]
        candidates_after = len(final_candidates)
        logger.info("[search.retrieval] candidates_after_limit=%d (limit=%d)", candidates_after, limit)
        logger.info(
            "[search.retrieval] DEBUG: candidate_count_before=%d candidate_count_after=%d filters_applied=%s",
            candidates_before,
            candidates_after,
            str(query_filter),
        )
        
        return final_candidates
    except Exception as exc:  # noqa: BLE001
        logger.exception("[search.retrieval] retrieval failed: %s", exc)
        return []
