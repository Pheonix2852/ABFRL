from __future__ import annotations

from models.search_models import SearchPlan
from search.normalizer import normalize_search_plan
from search.taxonomy import normalize_color


def _message_signals(message: str) -> set[str]:
    lower = message.lower()
    signals = set()
    if any(token in lower for token in ["more", "another", "different", "else"]):
        signals.add("continuation")
    if "cheaper" in lower:
        signals.add("cheaper")
    if any(token in lower for token in ["different color", "show blue", "blue one"]):
        signals.add("color_change")
    if any(token in lower for token in ["formal ones", "formal", "office"]):
        signals.add("formal")
    return signals


def _extract_inline_color(message: str) -> list[str]:
    lower = message.lower()
    colors = []
    for token in ["black", "blue", "red", "green", "white", "pink", "yellow", "purple", "brown", "beige", "navy"]:
        if token in lower:
            normalized = normalize_color(token)
            if normalized:
                colors.append(normalized)
    return colors


def merge_with_previous_plan(
    current_message: str,
    new_plan: SearchPlan,
    old_plan: SearchPlan,
) -> SearchPlan:
    if old_plan is None:
        return normalize_search_plan(new_plan)

    current_lower = current_message.lower()
    merged_data = old_plan.model_dump() if hasattr(old_plan, "model_dump") else old_plan.dict()
    new_data = new_plan.model_dump() if hasattr(new_plan, "model_dump") else new_plan.dict()

    for key, value in new_data.items():
        if value not in (None, [], ""):
            merged_data[key] = value

    merged = SearchPlan(**merged_data)
    signals = _message_signals(current_message)

    if "cheaper" in signals and old_plan.budget_max:
        if new_plan.budget_max is None or new_plan.budget_max == old_plan.budget_max:
            merged.budget_max = max(500, int(old_plan.budget_max * 0.8))
            if merged.budget_min and merged.budget_min > merged.budget_max:
                merged.budget_min = None

    if "color_change" in signals:
        inline_colors = _extract_inline_color(current_message)
        if inline_colors:
            merged.colors = inline_colors
        elif not new_plan.colors and old_plan.colors:
            merged.colors = []

    if "formal" in signals:
        merged.style = merged.style or "formal"
        merged.occasion = merged.occasion or "office"

    if "continuation" in signals:
        if not merged.category:
            merged.category = old_plan.category
        if not merged.gender:
            merged.gender = old_plan.gender
        if not merged.occasion:
            merged.occasion = old_plan.occasion
        if not merged.style:
            merged.style = old_plan.style
        if not merged.colors and old_plan.colors and "color_change" not in signals:
            merged.colors = old_plan.colors
        if merged.budget_min is None:
            merged.budget_min = old_plan.budget_min
        if merged.budget_max is None:
            merged.budget_max = old_plan.budget_max

    if not merged.colors and any(token in current_lower for token in ["show blue", "blue one"]):
        merged.colors = _extract_inline_color(current_message)

    return normalize_search_plan(merged)
