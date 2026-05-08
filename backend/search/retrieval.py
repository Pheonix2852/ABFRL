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


def _normalized_product_colors(product: dict[str, Any]) -> list[str]:
    normalized_colors = product.get("normalized_colors") or []
    if normalized_colors:
        return [str(color).strip().lower() for color in normalized_colors if str(color).strip()]
    colors = product.get("colors") or []
    return [taxonomy_service.normalize_color(color) or _safe_text(color).lower() for color in colors if _safe_text(color)]


def _build_filter(plan: SearchPlan) -> Filter:
    must = []

    # Filter by high-level category field (e.g., "ethnic_wear", "western_wear")
    if plan.category:
        must.append(FieldCondition(key="category", match=MatchValue(value=plan.category)))

    # Filter by product subcategory field (e.g., "kurta", "pants") with alias expansion
    if plan.subcategory:
        expanded = taxonomy_service.expand_aliases(plan.subcategory) if USE_NEW_TAXONOMY else [plan.subcategory]
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


def _matches_hard_constraints(product: dict[str, Any], plan: SearchPlan) -> bool:
    if plan.category and _safe_text(product.get("category")).lower() != plan.category.lower():
        return False

    if plan.subcategory:
        product_subcategory = _safe_text(product.get("subcategory")).lower()
        if not taxonomy_service.is_family_match(product_subcategory, plan.subcategory):
            return False

    if plan.gender == "men":
        genders = {str(item).lower() for item in product.get("gender_tags") or []}
        if not genders.intersection({"men", "unisex"}):
            return False
    elif plan.gender == "women":
        genders = {str(item).lower() for item in product.get("gender_tags") or []}
        if not genders.intersection({"women", "unisex"}):
            return False

    if plan.colors:
        wanted = {taxonomy_service.normalize_color(color) or _safe_text(color).lower() for color in plan.colors}
        product_colors = set(_normalized_product_colors(product))
        if not wanted.intersection(product_colors):
            return False

    return True


def _relax_soft_constraints(plan: SearchPlan) -> list[SearchPlan]:
    variants: list[SearchPlan] = []
    current = SearchPlan(**(plan.model_dump() if hasattr(plan, "model_dump") else plan.dict()))

    if current.occasion:
        variant = SearchPlan(**current.model_dump()) if hasattr(current, "model_dump") else SearchPlan(**current.dict())
        variant.occasion = None
        variants.append(variant)
        current = variant

    if current.style:
        variant = SearchPlan(**current.model_dump()) if hasattr(current, "model_dump") else SearchPlan(**current.dict())
        variant.style = None
        variants.append(variant)
        current = variant

    if (current.budget_min is not None or current.budget_max is not None) and not current.subcategory and not current.category:
        variant = SearchPlan(**current.model_dump()) if hasattr(current, "model_dump") else SearchPlan(**current.dict())
        if variant.budget_min is not None:
            variant.budget_min = max(0, int(variant.budget_min * 0.8))
        if variant.budget_max is not None:
            variant.budget_max = int(variant.budget_max * 1.2)
        variants.append(variant)

    return variants


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
        # Hard gating happens before ranking; this score stays for tie-breaking only.
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
        candidates_before = len(results)
        logger.info("[search.retrieval] candidates_before_lexical=%d", candidates_before)

        def _rank_results(result_set: list[Any]) -> list[dict[str, Any]]:
            ranked_candidates: list[dict[str, Any]] = []
            for result in result_set:
                product = result.payload or {}
                if not _matches_hard_constraints(product, plan):
                    continue
                semantic_similarity = float(result.score or 0.0)
                lexical_bonus = _lexical_bonus(product, plan)
                retrieval_score = _compute_retrieval_score(product, semantic_similarity, lexical_bonus, plan)
                ranked_candidates.append(
                    {
                        "product": product,
                        "semantic_similarity": semantic_similarity,
                        "lexical_bonus": lexical_bonus,
                        "retrieval_score": retrieval_score,
                        "used_category_fallback": False,
                    }
                )
            ranked_candidates.sort(key=lambda item: item.get("retrieval_score", 0.0), reverse=True)
            return ranked_candidates

        candidates = _rank_results(results)
        if not candidates:
            for relaxed_plan in _relax_soft_constraints(plan):
                relaxed_filter = _build_filter(relaxed_plan)
                relaxed_query_text = _build_query_text(relaxed_plan)
                relaxed_results = vectorstore.search(
                    client,
                    embed(relaxed_query_text or query_text or plan.intent or "fashion"),
                    top_k=max(limit * 2, 30),
                    query_filter=relaxed_filter,
                )
                candidates = _rank_results(relaxed_results)
                if candidates:
                    break

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
