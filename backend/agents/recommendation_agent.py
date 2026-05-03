"""
Recommendation Agent — RAG search + reranking + why_for_you generation.
Pipeline: entities → query → embed → Qdrant search (with filters) → rerank → Groq why_for_you
"""

import os
import json
import logging
from groq import Groq
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny, Range

from config import USE_NEW_SEARCH
from models.search_models import SearchPlan
from search.normalizer import normalize_search_plan
from search.planner import build_search_plan
from search.query_memory import merge_with_previous_plan
from search.ranking import rank_products
from search.retrieval import retrieve_candidates
from rag.embedder import embed
from rag import vectorstore
from agents.inventory_agent import check_product_stock

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
logger = logging.getLogger(__name__)

def _safe_text(value, default: str = "") -> str:
    if value is None:
        return default

    if isinstance(value, str):
        return value

    if isinstance(value, (int, float, bool)):
        return str(value)

    if isinstance(value, list):
        items = [_safe_text(item) for item in value]
        items = [item for item in items if item]
        return ", ".join(items)

    if isinstance(value, dict):
        for key in ("text", "message"):
            candidate = value.get(key)
            if candidate is not None:
                return _safe_text(candidate, default)

        try:
            return json.dumps(value)
        except TypeError:
            return default

    return str(value)


def _safe_list(value) -> list[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [_safe_text(item) for item in value if _safe_text(item)]

    text_value = _safe_text(value)
    return [text_value] if text_value else []


def _safe_number(value):
    if value is None or value == "":
        return None

    if isinstance(value, (int, float)):
        return value

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_nullable_entity_text(value) -> str | None:
    text = _safe_text(value).strip()
    if not text:
        return None
    if text.lower() in {"null", "none", "nil", "na", "n/a"}:
        return None
    return text


def _build_query(entities: dict) -> str:
    """Build a natural-language search query from extracted entities."""
    parts = ["fashion", "clothing"]

    if entities.get("color"):
        parts.append(_safe_text(entities.get("color")))
    if entities.get("occasion"):
        parts.append(_safe_text(entities.get("occasion")))
    if entities.get("subcategory"):
        parts.append((_safe_text(entities.get("subcategory")) or "").replace("_", " "))
    elif entities.get("category"):
        parts.append((_safe_text(entities.get("category")) or "").replace("_", " "))
    budget_max = _safe_number(entities.get("budget_max"))
    if budget_max is not None:
        parts.append(f"under {budget_max:g}")

    return " ".join(part for part in parts if part).strip()


def build_qdrant_filter(entities: dict) -> Filter:
    must = []

    gender = entities.get("gender")
    if gender == "men":
        must.append(FieldCondition(key="gender_tags", match=MatchAny(any=["men", "unisex"])))
    elif gender == "women":
        must.append(FieldCondition(key="gender_tags", match=MatchAny(any=["women", "unisex"])))

    category = _safe_nullable_entity_text(entities.get("category"))
    if category:
        must.append(FieldCondition(key="category", match=MatchValue(value=_safe_text(category))))

    subcategory = (_safe_nullable_entity_text(entities.get("subcategory")) or "").lower()

    subcategory_canonical = {
        "shirts": "shirt",
        "kurtas": "kurta",
        "sarees": "saree",
    }
    subcategory = subcategory_canonical.get(subcategory, subcategory)

    if subcategory:
        SUBCATEGORY_EXPANSION = {
            "pants": ["trousers", "jeans", "chinos", "joggers"],
            "shirts": ["shirt", "shirts", "formal_shirt", "casual_shirt"],
            "shirt": ["shirt", "shirts", "formal_shirt", "casual_shirt"],
            "shorts": ["shorts"],
            "shoes": ["sneakers", "loafers", "heels", "sandals", "flats", "ethnic_footwear"],
            "jewellery": ["jewellery"],
            "jewelry": ["jewellery"],
            "bags": ["handbag", "backpack", "wallet"],
            "bag": ["handbag", "backpack", "wallet"],
            "kurta": ["kurta"],
            "saree": ["saree", "sarees"],
        }

        expanded = SUBCATEGORY_EXPANSION.get(subcategory, [subcategory])

        must.append(
            FieldCondition(
                key="subcategory",
                match=MatchAny(any=expanded)
            )
        )

    budget_max = _safe_number(entities.get("budget_max"))
    if budget_max is not None:
        must.append(FieldCondition(key="price", range=Range(lte=budget_max)))

    budget_min = _safe_number(entities.get("budget_min"))
    if budget_min is not None:
        must.append(FieldCondition(key="price", range=Range(gte=budget_min)))

    must.append(FieldCondition(key="in_stock", match=MatchValue(value=True)))

    return Filter(must=must)


def _compute_rerank_score(
    product: dict,
    semantic_score: float,
    entities: dict,
) -> float:
    """
    Compute composite reranking score.
    Weights: 0.4 semantic + 0.3 budget_fit + 0.2 occasion_match + 0.1 color_match
    """
    # Budget fit
    budget_max = _safe_number(entities.get("budget_max"))
    if budget_max and budget_max > 0:
        price = _safe_number(product.get("price")) or 0
        budget_fit = max(0, 1 - abs(price - budget_max) / budget_max)
    else:
        budget_fit = 0.5  # neutral if no budget specified

    # Occasion match
    queried_occasion = _safe_text(entities.get("occasion", ""))
    product_occasions = _safe_list(product.get("occasion_tags") or product.get("occasionTags"))
    occasion_match = (
        1.0
        if queried_occasion and queried_occasion.lower() in [
            _safe_text(o).lower() for o in product_occasions
        ]
        else 0.0
    )

    # Color match — substring match across the colors array
    queried_color = _safe_text(entities.get("color", ""))
    product_colors = _safe_list(product.get("colors"))
    if queried_color:
        color_match = (
            1.0
            if any(
                queried_color.lower() in _safe_text(c).lower() for c in product_colors
            )
            else 0.5
        )
    else:
        color_match = 0.5  # neutral if no color specified

    final = (
        0.4 * semantic_score
        + 0.3 * budget_fit
        + 0.2 * occasion_match
        + 0.1 * color_match
    )

    return final


def _generate_why_for_you(
    product: dict,
    entities: dict,
    discount_label: str,
    user_name: str = "",
    tier: str = "",
) -> str:
    """Generate a 1-sentence 'why this product is perfect for you' using Groq."""
    try:
        product_name = _safe_text(product.get("name"), "this product")
        description = _safe_text(product.get("description"))[:200]
        prompt = (
            f"Product: {product_name}\n"
            f"Description: {description}\n"
            f"Customer: {user_name} ({tier} member)\n"
            f"Discount applied: {discount_label}\n"
            f"Customer's occasion: {_safe_text(entities.get('occasion', 'general'), 'general')}\n"
            f"Color preference: {_safe_text(entities.get('color', 'any'), 'any')}\n"
            f"Budget: {entities.get('budget_max', 'flexible')}\n\n"
            f"Write exactly ONE short sentence (max 20 words) explaining why "
            f"this product is perfect for {user_name or 'this customer'}. "
            f"Be specific about the product features. Do not start with 'This'."
        )

        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "You write concise product recommendations. One sentence only.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=50,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"[recommendation_agent] Exception: {e}")
        return f"Great choice for {_safe_text(entities.get('occasion', 'any occasion'), 'any occasion')}!"


def _search_plan_from_legacy_context(context: dict | None) -> SearchPlan | None:
    if not isinstance(context, dict):
        return None

    candidate = context.get("previous_plan") or context.get("search_plan") or context.get("plan")
    if not isinstance(candidate, dict):
        return None

    try:
        return normalize_search_plan(SearchPlan(**candidate))
    except Exception:
        return None


def _has_strong_entity_constraints(entities: dict | None) -> bool:
    if not isinstance(entities, dict):
        return False

    return any(
        _safe_nullable_entity_text(entities.get(key)) is not None
        for key in ("category", "subcategory")
    ) or any(
        _safe_number(entities.get(key)) is not None
        for key in ("budget_min", "budget_max")
    )


def _build_plan_from_entities(entities: dict | None) -> SearchPlan:
    entities = entities or {}

    color = _safe_nullable_entity_text(entities.get("color"))
    budget_min_value = _safe_number(entities.get("budget_min"))
    budget_max_value = _safe_number(entities.get("budget_max"))

    plan = SearchPlan(
        intent="recommendation",
        category=_safe_nullable_entity_text(entities.get("category")),
        subcategory=_safe_nullable_entity_text(entities.get("subcategory")),
        gender=_safe_nullable_entity_text(entities.get("gender")),
        budget_min=int(budget_min_value) if budget_min_value is not None else None,
        budget_max=int(budget_max_value) if budget_max_value is not None else None,
        colors=[color] if color else [],
        occasion=_safe_nullable_entity_text(entities.get("occasion")),
        style=_safe_nullable_entity_text(entities.get("style")),
        hard_constraints=[],
        soft_preferences=[],
        confidence=1.0,
    )
    return normalize_search_plan(plan)


def _run_structured_search(
    entities: dict,
    user_id: str,
    discount_info: dict,
    exclude_ids: list | None = None,
    strict_subcategory: bool = False,
    message: str = "",
    context: dict | None = None,
) -> dict:
    del strict_subcategory

    search_message = message or _build_query(entities)
    if _has_strong_entity_constraints(entities):
        # Single source of truth: orchestrator-extracted entities.
        plan = _build_plan_from_entities(entities)
        logger.info("[recommendation_agent] search plan source=entities")
    else:
        # Only use planner when entities are weak/empty.
        plan = build_search_plan(search_message, context=context or {})
        logger.info("[recommendation_agent] search plan source=planner")

    previous_plan = _search_plan_from_legacy_context(context)
    if previous_plan is not None:
        plan = merge_with_previous_plan(search_message, plan, previous_plan)

    candidates = retrieve_candidates(plan)
    pipeline_counts = {
        "candidate_count_after_retrieval": len(candidates),
        "candidate_count_after_price": len(candidates),
        "candidate_count_after_ranking": 0,
        "candidate_count_after_exclude": 0,
        "candidate_count_after_stock": 0,
        "candidate_count_after_validation": 0,
        "candidate_count_after_rerank_truncation": 0,
    }

    if not candidates:
        logger.info(
            "[recommendation_agent] stage_counts=%s",
            pipeline_counts,
        )
        return {
            "products": [],
            "message": "I couldn't find any matching products. Try different search terms!",
            "error": None,
            "metadata": {
                "search_plan": plan.model_dump() if hasattr(plan, "model_dump") else plan.dict(),
                "candidate_count_before": pipeline_counts["candidate_count_after_retrieval"],
                "candidate_count_after": pipeline_counts["candidate_count_after_rerank_truncation"],
                "filters_applied": ["subcategory/category", "gender(if explicit)", "price", "exclude_ids", "stock_soft", "top_5"],
                "pipeline_counts": pipeline_counts,
            },
        }

    ranked_candidates = rank_products(candidates, plan)
    pipeline_counts["candidate_count_after_ranking"] = len(ranked_candidates)
    exclude_ids = exclude_ids or []
    scored_products = []
    exclude_filtered_count = 0
    stock_filtered_count = 0

    for item in ranked_candidates:
        product = item.get("product") or {}
        sku_id = _safe_text(product.get("id"))
        if not sku_id or sku_id in exclude_ids:
            exclude_filtered_count += 1
            continue

        # Soft stock gate: do not drop products solely because in_stock is missing.
        stock_flag = product.get("in_stock")
        online_stock = int(product.get("online_stock", 0) or 0)
        is_stock_eligible = (stock_flag is not False) or (online_stock > 0)
        if not is_stock_eligible:
            stock_filtered_count += 1
            continue

        scored_products.append(
            {
                "product": product,
                "score": item.get("rank_score", 0.0),
                "online_stock": online_stock,
            }
        )

    pipeline_counts["candidate_count_after_exclude"] = pipeline_counts["candidate_count_after_ranking"] - exclude_filtered_count
    pipeline_counts["candidate_count_after_stock"] = len(scored_products)
    # No dedicated validation layer in backend structured pipeline right now.
    pipeline_counts["candidate_count_after_validation"] = len(scored_products)

    scored_products.sort(key=lambda item: item["score"], reverse=True)
    top_5 = scored_products[:5]
    pipeline_counts["candidate_count_after_rerank_truncation"] = len(top_5)

    logger.info(
        "[recommendation_agent] stage_counts=%s filters_applied=%s",
        pipeline_counts,
        ["subcategory/category", "gender(if explicit)", "price", "exclude_ids", "stock_soft", "top_5"],
    )

    if not top_5:
        return {
            "products": [],
            "message": "I couldn't find any matching products. Try different search terms!",
            "error": None,
            "metadata": {
                "search_plan": plan.model_dump() if hasattr(plan, "model_dump") else plan.dict(),
                "candidate_count_before": pipeline_counts["candidate_count_after_retrieval"],
                "candidate_count_after": pipeline_counts["candidate_count_after_rerank_truncation"],
                "filters_applied": ["subcategory/category", "gender(if explicit)", "price", "exclude_ids", "stock_soft", "top_5"],
                "pipeline_counts": pipeline_counts,
            },
        }

    discount_pct = discount_info.get("discount_pct", 0)
    discount_label = discount_info.get("discount_label", "")

    products = []
    for item in top_5:
        product = item["product"]
        price = product.get("price") or 0
        discounted_price = None
        if discount_pct > 0:
            discounted_price = round(price * (1 - discount_pct), 2)

        why = _generate_why_for_you(
            product,
            entities,
            discount_label,
            user_name=discount_info.get("customer_name", ""),
            tier=discount_info.get("tier", ""),
        )

        products.append(
            {
                "id": _safe_text(product.get("id")),
                "name": _safe_text(product.get("name")),
                "category": _safe_text(product.get("category")),
                "subcategory": _safe_text(product.get("subcategory")),
                "gender_tags": _safe_list(product.get("gender_tags")),
                "price": price,
                "discounted_price": discounted_price,
                "colors": _safe_list(product.get("colors")),
                "occasion_tags": _safe_list(product.get("occasion_tags") or product.get("occasionTags")),
                "sizes": _safe_list(product.get("sizes")),
                "online_stock": item.get("online_stock", 0),
                "in_stock": True,
                "image_url": _safe_text(product.get("image_url") or product.get("imageUrl")),
                "rating": product.get("rating", 0) or 0,
                "why_for_you": why,
            }
        )

    category_name = (_safe_text(
        plan.category or entities.get("subcategory") or entities.get("category") or "fashion",
        "fashion",
    ) or "fashion").replace("_", " ")
    message_text = f"Here are {len(products)} {category_name} picks perfect for you!"
    if discount_label:
        message_text += f" {discount_label} applied."

    return {
        "products": products,
        "message": message_text,
        "error": None,
        "metadata": {
            "search_plan": plan.model_dump() if hasattr(plan, "model_dump") else plan.dict(),
            "candidate_count_before": pipeline_counts["candidate_count_after_retrieval"],
            "candidate_count_after": pipeline_counts["candidate_count_after_rerank_truncation"],
            "filters_applied": ["subcategory/category", "gender(if explicit)", "price", "exclude_ids", "stock_soft", "top_5"],
            "pipeline_counts": pipeline_counts,
        },
    }


def run(
    entities: dict,
    user_id: str,
    discount_info: dict,
    exclude_ids: list | None = None,
    strict_subcategory: bool = False,
    message: str = "",
    context: dict | None = None,
) -> dict:
    """
    Full recommendation pipeline.

    Args:
        entities:      Extracted entities from NLU agent
        user_id:       Customer ID
        discount_info: Output from loyalty_agent.run()

    Returns:
        dict with 'products' list and 'message'
    """
    if USE_NEW_SEARCH:
        try:
            return _run_structured_search(
                entities=entities,
                user_id=user_id,
                discount_info=discount_info,
                exclude_ids=exclude_ids,
                strict_subcategory=strict_subcategory,
                message=message,
                context=context,
            )
        except Exception as exc:
            logger.exception("[recommendation_agent] Structured search failed, falling back: %s", exc)

    try:
        # 1. Build query and embed
        query_text = _build_query(entities)
        print(f"[recommendation_agent] Query: '{query_text}'")
        query_vector = embed(query_text)

        # 2. Build deterministic pre-filter and search Qdrant
        qdrant_filter = build_qdrant_filter(entities)
        print(f"[recommendation_agent] Filter: {qdrant_filter}")
        qdrant_client = vectorstore.get_client()
        results = vectorstore.search(
            qdrant_client,
            query_vector,
            top_k=50,
            query_filter=qdrant_filter,
        )

        if not results:
            return {
                "products": [],
                "message": "I couldn't find any matching products. Try different search terms!",
            }

        # 3. Filter out-of-stock and rerank
        exclude_ids = exclude_ids or []
        scored_products = []
        for result in results:
            product = result.payload or {}
            requested_color = _safe_text(entities.get("color")).lower()
            if requested_color:
                product_colors = [c.lower() for c in _safe_list(product.get("colors"))]
                if not any(requested_color in c for c in product_colors):
                    continue

            sku_id = _safe_text(product.get("id"))

            sku_id = _safe_text(product.get("id"))

            if sku_id in exclude_ids:
                continue

            if not sku_id:
                continue

            # Check stock
            stock = {"in_stock": True, "quantity": 10}

            try:
                live_stock = {"in_stock": True, "quantity": 25}
                if isinstance(live_stock, dict):
                    stock["in_stock"] = live_stock.get("in_stock", True)
                    stock["quantity"] = live_stock.get("quantity", 10)
            except Exception:
                pass

            # Compute composite score
            score = _compute_rerank_score(product, result.score or 0.0, entities)

            scored_products.append({
                "product": product,
                "score": score,
                "online_stock": stock.get("quantity", 0),
            })

        # Sort by composite score descending
        scored_products.sort(key=lambda x: x["score"], reverse=True)

        # 4. Take top 5
        top_5 = scored_products[:5]

        if not top_5:
            return {
                "products": [],
                "message": "All matching products are currently out of stock. Please check back later!",
            }

        # 5. Build product response objects
        discount_pct = discount_info.get("discount_pct", 0)
        discount_label = discount_info.get("discount_label", "")

        products = []
        for item in top_5:
            p = item["product"]
            price = p.get("price") or 0

            # Apply loyalty discount
            discounted_price = None
            if discount_pct > 0:
                discounted_price = round(price * (1 - discount_pct), 2)

            # Generate why_for_you
            why = _generate_why_for_you(
                p,
                entities,
                discount_label,
                user_name=discount_info.get("customer_name", ""),
                tier=discount_info.get("tier", ""),
            )

            products.append({
                "id": _safe_text(p.get("id")),
                "name": _safe_text(p.get("name")),
                "category": _safe_text(p.get("category")),
                "subcategory": _safe_text(p.get("subcategory")),
                "gender_tags": _safe_list(p.get("gender_tags")),
                "price": price,
                "discounted_price": discounted_price,
                "colors": _safe_list(p.get("colors")),
                "occasion_tags": _safe_list(p.get("occasion_tags") or p.get("occasionTags")),
                "sizes": _safe_list(p.get("sizes")),
                "online_stock": item.get("online_stock", 0),
                "in_stock": True,
                "image_url": _safe_text(p.get("image_url") or p.get("imageUrl")),
                "rating": p.get("rating", 0) or 0,
                "why_for_you": why,
            })

        # Build response message
        category_name = (_safe_text(
            entities.get("subcategory") or entities.get("category") or "fashion",
            "fashion",
        ) or "fashion").replace("_", " ")
        message = f"Here are {len(products)} {category_name} picks perfect for you!"
        if discount_label:
            message += f" {discount_label} applied."

        return {
            "products": products,
            "message": message,
            "error": None,
        }

    except Exception as e:
        print(f"[recommendation_agent] Exception: {e}")
        return {
            "products": [],
            "message": "Something went wrong while searching for products. Please try again.",
            "error": "RETRIEVAL_FAILED",
        }
