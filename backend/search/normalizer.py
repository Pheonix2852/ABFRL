from __future__ import annotations

from collections.abc import Iterable

from models.search_models import SearchPlan
from search.taxonomy import normalize_category, normalize_color


SUBCATEGORY_SINGULAR = {
    "shirts": "shirt",
    "kurtas": "kurta",
    "sarees": "saree",
}


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = str(value).strip().lower()
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _sanitize_nullable_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.lower() in {"null", "none", "nil", "na", "n/a"}:
        return None
    return text


def _normalize_subcategory(value: str | None) -> str | None:
    text = _sanitize_nullable_text(value)
    if text is None:
        return None
    return SUBCATEGORY_SINGULAR.get(text.lower(), text.lower())


def normalize_search_plan(plan: SearchPlan) -> SearchPlan:
    data = plan.model_dump() if hasattr(plan, "model_dump") else plan.dict()
    normalized = SearchPlan(**data)

    normalized.intent = _sanitize_nullable_text(normalized.intent) or "recommendation"
    normalized.category = normalize_category(normalized.category)
    if normalized.category == "apparel":
        normalized.category = None
    normalized.subcategory = _normalize_subcategory(normalized.subcategory)
    normalized.gender = _sanitize_nullable_text(normalized.gender)
    normalized.occasion = _sanitize_nullable_text(normalized.occasion)
    normalized.style = _sanitize_nullable_text(normalized.style)
    normalized.colors = [
        color
        for color in (normalize_color(item) for item in normalized.colors)
        if color
    ]
    normalized.colors = _dedupe(normalized.colors)
    normalized.hard_constraints = _dedupe(normalized.hard_constraints)
    normalized.soft_preferences = _dedupe(normalized.soft_preferences)

    combined_text = " ".join(
        [
            normalized.intent or "",
            normalized.style or "",
            normalized.occasion or "",
            " ".join(normalized.hard_constraints),
            " ".join(normalized.soft_preferences),
            " ".join(normalized.colors),
        ]
    ).lower()

    if any(token in combined_text for token in ["cheap", "budget", "affordable", "low price"]):
        normalized.intent = "budget"
        if "budget" not in normalized.soft_preferences:
            normalized.soft_preferences.append("budget")

    if any(token in combined_text for token in ["luxury", "high-end", "premium"]):
        normalized.style = "premium"

    if any(token in combined_text for token in ["classic black", "jet black", "midnight black"]):
        if "black" not in normalized.colors:
            normalized.colors.append("black")

    normalized.colors = _dedupe(normalized.colors)
    return normalized
