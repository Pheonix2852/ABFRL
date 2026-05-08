from __future__ import annotations

from models.search_models import SearchPlan
from search.normalizer import normalize_search_plan
from services import taxonomy_service


def _message_signals(message: str) -> set[str]:
    lower = message.lower().strip()
    signals = set()
    if any(token in lower for token in ["more", "another", "else"]):
        signals.add("more")
    if "cheaper" in lower:
        signals.add("cheaper")
    if any(token in lower for token in ["different color", "different colours", "blue instead", "show red", "show blue", "red instead"]):
        signals.add("color_change")
    if any(token in lower for token in ["formal ones", "formal", "office", "casual"]):
        signals.add("style_change")
    return signals


def _extract_inline_color(message: str) -> list[str]:
    normalized = taxonomy_service.normalize_query_text(message)
    colors = []
    for token in normalized.split():
        color = taxonomy_service.normalize_color(token)
        if color and color not in colors:
            colors.append(color)
    return colors


def _rebuild_constraints(plan: SearchPlan) -> SearchPlan:
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


def _should_merge(current_message: str, new_plan: SearchPlan) -> bool:
    lower = current_message.lower().strip()
    family_present = bool(new_plan.category or new_plan.subcategory or new_plan.style_mode)

    if any(token in lower for token in ["cheaper", "more", "another", "else", "different color", "different colours", "blue instead", "red instead", "show red", "show blue", "formal ones"]):
        return True

    if not family_present and (new_plan.colors or new_plan.style or new_plan.occasion or new_plan.gender):
        return True

    return False


def _apply_follow_up(current_message: str, new_plan: SearchPlan, old_plan: SearchPlan) -> SearchPlan:
    merged = SearchPlan(**(old_plan.model_dump() if hasattr(old_plan, "model_dump") else old_plan.dict()))
    signals = _message_signals(current_message)

    if new_plan.category:
        merged.category = new_plan.category
    if new_plan.subcategory:
        merged.subcategory = new_plan.subcategory
    if new_plan.style_mode:
        merged.style_mode = new_plan.style_mode
    if new_plan.gender:
        merged.gender = new_plan.gender
    if new_plan.occasion:
        merged.occasion = new_plan.occasion
    if new_plan.style:
        merged.style = new_plan.style

    if "cheaper" in signals and old_plan.budget_max:
        merged.budget_max = max(500, int(old_plan.budget_max * 0.8))
        if merged.budget_min and merged.budget_min > merged.budget_max:
            merged.budget_min = None
    else:
        if new_plan.budget_min is not None:
            merged.budget_min = new_plan.budget_min
        if new_plan.budget_max is not None:
            merged.budget_max = new_plan.budget_max

    if "color_change" in signals:
        inline_colors = _extract_inline_color(current_message)
        if inline_colors:
            merged.colors = inline_colors
        elif new_plan.colors:
            merged.colors = new_plan.colors
        else:
            merged.colors = []
    elif new_plan.colors:
        merged.colors = new_plan.colors

    if "style_change" in signals:
        if "formal" in current_message.lower():
            merged.style = "formal"
            merged.occasion = merged.occasion or "office"
        elif "casual" in current_message.lower():
            merged.style = "casual"

    if "more" in signals:
        merged.soft_preferences = list(dict.fromkeys([*merged.soft_preferences, "continue" ]))

    return _rebuild_constraints(merged)


def merge_with_previous_plan(
    current_message: str,
    new_plan: SearchPlan,
    old_plan: SearchPlan,
) -> SearchPlan:
    if old_plan is None:
        return normalize_search_plan(new_plan)

    if not _should_merge(current_message, new_plan):
        return _rebuild_constraints(SearchPlan(**(new_plan.model_dump() if hasattr(new_plan, "model_dump") else new_plan.dict())))

    merged = _apply_follow_up(current_message, new_plan, old_plan)
    return normalize_search_plan(merged)
