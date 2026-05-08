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
from services import taxonomy_service

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


def _extract_category(message: str) -> str | None:
    family = taxonomy_service.detect_explicit_product_noun(message)
    if not family or family == "coordinated_look":
        return None
    return taxonomy_service.get_category_for_family(family)


def _extract_subcategory(message: str) -> str | None:
    family = taxonomy_service.detect_explicit_product_noun(message)
    if not family or family == "coordinated_look":
        return None
    return taxonomy_service.normalize_term(family)


def _extract_colors(message: str) -> list[str]:
    colors: list[str] = []
    normalized = taxonomy_service.normalize_query_text(message)
    for token in normalized.split():
        color = taxonomy_service.normalize_color(token)
        if color and color not in {"cheap", "premium"} and color not in colors:
            colors.append(color)
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
    style_mode = None
    normalized_message = taxonomy_service.normalize_query_text(message)
    if any(token in normalized_message for token in ["outfit", "outfits", "coordinated_look"]):
        style_mode = "coordinated_look"

    explicit_constraints: list[str] = []
    if category:
        explicit_constraints.append(f"category:{category}")
    if subcategory:
        explicit_constraints.append(f"subcategory:{subcategory}")
    if colors:
        explicit_constraints.extend(f"color:{color}" for color in colors)
    if _infer_gender(message):
        explicit_constraints.append(f"gender:{_infer_gender(message)}")

    inferred_preferences: list[str] = []
    if budget_min is not None or budget_max is not None:
        inferred_preferences.append("budget")
    if _infer_occasion(message):
        inferred_preferences.append(f"occasion:{_infer_occasion(message)}")
    if _infer_style(message):
        inferred_preferences.append(f"style:{_infer_style(message)}")

    plan = SearchPlan(
        intent="recommendation",
        category=category,
        subcategory=subcategory,
        style_mode=style_mode,
        gender=_infer_gender(message),
        budget_min=budget_min,
        budget_max=budget_max,
        colors=colors,
        occasion=_infer_occasion(message),
        style=_infer_style(message),
        allow_cross_category=style_mode == "coordinated_look" or not (category or subcategory),
        explicit_constraints=explicit_constraints,
        inferred_preferences=inferred_preferences,
        hard_constraints=explicit_constraints,
        soft_preferences=inferred_preferences,
        confidence=0.35,
    )
    return normalize_search_plan(plan)


def _parse_llm_plan(payload: dict[str, Any]) -> SearchPlan:
    plan = SearchPlan(
        intent=str(_safe_nullable_text(payload.get("intent")) or "recommendation"),
        category=_safe_nullable_text(payload.get("category")),
        subcategory=_safe_nullable_text(payload.get("subcategory")),
        style_mode=_safe_nullable_text(payload.get("style_mode")),
        gender=_safe_nullable_text(payload.get("gender")),
        budget_min=_safe_int(payload.get("budget_min")),
        budget_max=_safe_int(payload.get("budget_max")),
        colors=[str(color) for color in payload.get("colors") or [] if str(color).strip()],
        occasion=_safe_nullable_text(payload.get("occasion")),
        style=_safe_nullable_text(payload.get("style")),
        allow_cross_category=bool(payload.get("allow_cross_category", False)),
        explicit_constraints=[str(item) for item in payload.get("explicit_constraints") or [] if str(item).strip()],
        inferred_preferences=[str(item) for item in payload.get("inferred_preferences") or [] if str(item).strip()],
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
        "Use ONLY taxonomy-driven family and color terms.\n"
        "Infer category, subcategory, budget, color, occasion.\n"
        "Return keys: intent, category, subcategory, style_mode, gender, budget_min, budget_max, colors, occasion, style, allow_cross_category, explicit_constraints, inferred_preferences, hard_constraints, soft_preferences, confidence.\n"
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

        normalized_message = taxonomy_service.normalize_query_text(message)
        plan = _try_llm_plan(normalized_message, context)
        if plan is None:
            plan = _build_fallback_plan(normalized_message)

        explicit_family = taxonomy_service.detect_explicit_product_noun(normalized_message)
        if explicit_family == "coordinated_look":
            plan.style_mode = "coordinated_look"
            plan.allow_cross_category = True
        elif explicit_family:
            if not plan.subcategory:
                plan.subcategory = taxonomy_service.normalize_term(explicit_family)
            if not plan.category:
                inferred_category = taxonomy_service.get_category_for_family(explicit_family)
                if inferred_category:
                    plan.category = inferred_category

        if not plan.category and plan.subcategory:
            inferred_category = taxonomy_service.get_category_for_family(plan.subcategory)
            if inferred_category:
                plan.category = inferred_category

        if not plan.allow_cross_category:
            exploratory_tokens = ["something nice", "fashion ideas", "suggest outfits", "outfit ideas", "recommend something", "anything nice"]
            plan.allow_cross_category = any(token in normalized_message for token in exploratory_tokens)

        if plan.style_mode == "coordinated_look":
            plan.allow_cross_category = True

        explicit_constraints: list[str] = []
        if plan.category:
            explicit_constraints.append(f"category:{plan.category}")
        if plan.subcategory:
            explicit_constraints.append(f"subcategory:{plan.subcategory}")
        if plan.gender:
            explicit_constraints.append(f"gender:{plan.gender}")
        explicit_constraints.extend(f"color:{color}" for color in plan.colors)

        inferred_preferences: list[str] = []
        if plan.occasion:
            inferred_preferences.append(f"occasion:{plan.occasion}")
        if plan.style:
            inferred_preferences.append(f"style:{plan.style}")
        if plan.budget_min is not None or plan.budget_max is not None:
            inferred_preferences.append("budget")

        plan.explicit_constraints = list(dict.fromkeys(explicit_constraints))
        plan.inferred_preferences = list(dict.fromkeys(inferred_preferences))
        plan.hard_constraints = list(plan.explicit_constraints)
        plan.soft_preferences = list(dict.fromkeys([*plan.soft_preferences, *plan.inferred_preferences]))

        return normalize_search_plan(plan)
    except Exception as exc:  # noqa: BLE001
        logger.exception("[search.planner] Falling back after failure: %s", exc)
        return _build_fallback_plan(taxonomy_service.normalize_query_text(message))
