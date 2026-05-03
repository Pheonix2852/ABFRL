from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from groq import Groq

from config import ENABLE_LLM_RERANK
from models.search_models import SearchPlan
from search.normalizer import normalize_search_plan
from search.taxonomy import load_synonyms, load_taxonomy, normalize_category

logger = logging.getLogger(__name__)


def _get_groq_client() -> Groq | None:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    try:
        return Groq(api_key=api_key)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[search.planner] Groq client unavailable: %s", exc)
        return None


def _extract_json_blob(text: str) -> str | None:
    if not text:
        return None
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    return match.group(0) if match else None


def _safe_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _safe_nullable_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.lower() in {"null", "none", "nil", "na", "n/a"}:
        return None
    return text


def _infer_gender(message: str) -> str | None:
    lower = message.lower()
    if any(token in lower for token in ["for men", "mens", "men's", "male", "gents"]):
        return "men"
    if any(token in lower for token in ["for women", "womens", "women's", "female", "ladies"]):
        return "women"
    return None


def _infer_occasion(message: str) -> str | None:
    lower = message.lower()
    for occasion in ["wedding", "festive", "office", "party", "casual", "traditional"]:
        if occasion in lower:
            return occasion
    return None


def _infer_style(message: str) -> str | None:
    lower = message.lower()
    for style in ["formal", "classy", "elegant", "premium", "luxury", "traditional"]:
        if style in lower:
            return style
    return None


def _map_taxonomy_to_qdrant_category(taxonomy_category: str | None) -> str | None:
    """
    Map taxonomy category names (from load_taxonomy()) to Qdrant category values.
    
    Taxonomy has: "kurtas", "sarees", "jeans", "shirts", "dresses", "jackets", "trousers"
    Qdrant has:   "ethnic_wear", "western_wear", "accessories", "footwear"
    """
    if not taxonomy_category:
        return None
    
    mapping = {
        "kurtas": "ethnic_wear",
        "sarees": "ethnic_wear",
        "jackets": "western_wear",
        "shirts": "western_wear",
        "trousers": "western_wear",
        "jeans": "western_wear",
        "dresses": "western_wear",
    }
    
    return mapping.get(taxonomy_category.lower())


def _extract_category(message: str) -> str | None:
    lower = message.lower()
    taxonomy = load_taxonomy()
    for canonical, aliases in taxonomy.items():
        candidates = [canonical, *aliases]
        for candidate in sorted(candidates, key=len, reverse=True):
            if candidate and candidate in lower:
                # Map taxonomy category to Qdrant category
                return _map_taxonomy_to_qdrant_category(canonical)
    return None


def _extract_subcategory(message: str) -> str | None:
    """
    Extract product subcategory (kurta, pants, shirt, etc.) from user message.
    Uses a mapping of common product types normalized by NLU rules.
    """
    lower = message.lower()
    
    # Subcategory mapping — based on NLU normalizer
    subcategory_map = {
        "kurta": ["kurta", "kurti", "kurtas"],
        "pants": ["pant", "pants", "trouser", "trousers", "slacks", "bottoms"],
        "shirt": ["shirt", "shirts", "formal shirt", "casual shirt"],
        "jeans": ["jean", "jeans", "denim"],
        "tshirt": ["tshirt", "tee", "t-shirt"],
        "shorts": ["short", "shorts"],
        "shoes": ["shoe", "shoes", "footwear", "sneaker", "sneakers", "loafer", "loafers", "heel", "heels", "sandal", "sandals"],
        "jewellery": ["jewel", "jewellery", "jewelry", "necklace", "earring", "earrings"],
        "bags": ["purse", "bag", "bags", "handbag"],
        "saree": ["saree", "sarees", "sari"],
        "dress": ["dress", "gown", "one piece", "midi"],
    }
    
    # Check each subcategory and its aliases
    for canonical, aliases in subcategory_map.items():
        candidates = [canonical, *aliases]
        # Sort by length descending to match longer phrases first
        for candidate in sorted(set(candidates), key=len, reverse=True):
            if candidate and candidate in lower:
                return canonical
    
    return None


def _extract_colors(message: str) -> list[str]:
    lower = message.lower()
    synonyms = load_synonyms()
    colors: list[str] = []
    for canonical, aliases in synonyms.items():
        if canonical in {"cheap", "premium"}:
            continue
        candidates = [canonical, *aliases]
        if any(candidate in lower for candidate in sorted(candidates, key=len, reverse=True)):
            colors.append(canonical)
    return colors


def _extract_budget(message: str) -> tuple[int | None, int | None]:
    lower = message.lower()
    between = re.search(r"(?:between|from)\s+₹?\s*(\d[\d,]*)\s+(?:and|to)\s+₹?\s*(\d[\d,]*)", lower)
    if between:
        return _safe_int(between.group(1)), _safe_int(between.group(2))

    under = re.search(r"(?:under|below|less than|within)\s+₹?\s*(\d[\d,]*)", lower)
    if under:
        return None, _safe_int(under.group(1))

    over = re.search(r"(?:over|above|more than|at least)\s+₹?\s*(\d[\d,]*)", lower)
    if over:
        return _safe_int(over.group(1)), None

    exact = re.search(r"₹\s*(\d[\d,]*)", lower)
    if exact:
        value = _safe_int(exact.group(1))
        return None, value

    return None, None


def _build_fallback_plan(message: str) -> SearchPlan:
    budget_min, budget_max = _extract_budget(message)
    colors = _extract_colors(message)
    category = _extract_category(message)
    subcategory = _extract_subcategory(message)
    hard_constraints: list[str] = []
    if category:
        hard_constraints.append(category)
    if subcategory:
        hard_constraints.append(subcategory)
    if budget_min is not None:
        hard_constraints.append(f"budget_min:{budget_min}")
    if budget_max is not None:
        hard_constraints.append(f"budget_max:{budget_max}")

    plan = SearchPlan(
        intent="recommendation",
        category=category,
        subcategory=subcategory,
        gender=_infer_gender(message),
        budget_min=budget_min,
        budget_max=budget_max,
        colors=colors,
        occasion=_infer_occasion(message),
        style=_infer_style(message),
        hard_constraints=hard_constraints,
        soft_preferences=["budget"] if "cheap" in message.lower() else [],
        confidence=0.35,
    )
    return normalize_search_plan(plan)


def _parse_llm_plan(payload: dict[str, Any]) -> SearchPlan:
    plan = SearchPlan(
        intent=str(_safe_nullable_text(payload.get("intent")) or "recommendation"),
        category=_safe_nullable_text(payload.get("category")),
        subcategory=_safe_nullable_text(payload.get("subcategory")),
        gender=_safe_nullable_text(payload.get("gender")),
        budget_min=_safe_int(payload.get("budget_min")),
        budget_max=_safe_int(payload.get("budget_max")),
        colors=[str(color) for color in payload.get("colors") or [] if str(color).strip()],
        occasion=_safe_nullable_text(payload.get("occasion")),
        style=_safe_nullable_text(payload.get("style")),
        hard_constraints=[str(item) for item in payload.get("hard_constraints") or [] if str(item).strip()],
        soft_preferences=[str(item) for item in payload.get("soft_preferences") or [] if str(item).strip()],
        confidence=float(payload.get("confidence") or 0.6),
    )
    return normalize_search_plan(plan)


def _try_llm_plan(message: str, context: dict | None = None) -> SearchPlan | None:
    client = _get_groq_client()
    if client is None:
        return None

    context_text = json.dumps(context, ensure_ascii=False) if context else "{}"
    prompt = (
        "Convert retail query into JSON only.\n"
        "Use apparel taxonomy.\n"
        "Infer category, subcategory, budget, color, occasion.\n"
        "Return keys: intent, category, subcategory, gender, budget_min, budget_max, colors, occasion, style, hard_constraints, soft_preferences, confidence.\n"
        f"Context: {context_text}\n"
        f"Query: {message}"
    )

    response = client.chat.completions.create(
        model=os.getenv("SEARCH_PLANNER_MODEL", "llama-3.1-8b-instant"),
        messages=[
            {"role": "system", "content": "You return valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        max_tokens=220,
    )

    content = response.choices[0].message.content or ""
    json_blob = _extract_json_blob(content)
    if not json_blob:
        return None

    try:
        parsed = json.loads(json_blob)
        if isinstance(parsed, dict):
            return _parse_llm_plan(parsed)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[search.planner] Could not parse LLM response: %s", exc)
    return None


def build_search_plan(message: str, context: dict | None = None) -> SearchPlan:
    try:
        if ENABLE_LLM_RERANK:
            logger.info("[search.planner] LLM rerank flag enabled for future use")

        plan = _try_llm_plan(message, context)
        if plan is None:
            plan = _build_fallback_plan(message)

        # Safeguard: keep explicit apparel type queries strict even if LLM misses subcategory.
        if not plan.subcategory:
            plan.subcategory = _extract_subcategory(message)

        if context:
            context_plan = context.get("search_plan") or context.get("plan")
            if isinstance(context_plan, dict):
                context_candidate = SearchPlan(**context_plan)
                if not plan.category:
                    plan.category = normalize_category(context_candidate.category)
                if not plan.subcategory:
                    plan.subcategory = context_candidate.subcategory
                if not plan.colors:
                    plan.colors = context_candidate.colors
                if not plan.occasion:
                    plan.occasion = context_candidate.occasion
                if not plan.style:
                    plan.style = context_candidate.style
                if plan.budget_min is None:
                    plan.budget_min = context_candidate.budget_min
                if plan.budget_max is None:
                    plan.budget_max = context_candidate.budget_max
                if not plan.gender:
                    plan.gender = context_candidate.gender

        return normalize_search_plan(plan)
    except Exception as exc:  # noqa: BLE001
        logger.exception("[search.planner] Falling back after failure: %s", exc)
        return _build_fallback_plan(message)
