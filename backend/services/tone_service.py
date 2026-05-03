from __future__ import annotations

from services import taxonomy_service


def _family_label(family: str | None) -> str:
    normalized = taxonomy_service.normalize_term(family)
    if not normalized:
        return "fashion"

    if normalized == "footwear_general":
        return "footwear"

    return normalized.replace("_", " ")


def build_recommendation_message(
    count: int,
    family: str | None,
    budget_max: int | None = None,
    discount_label: str | None = None,
    used_fallback: bool = False,
) -> str:
    label = _family_label(family)

    if used_fallback and family:
        message = f"No exact {label} found, showing the closest premium options."
    elif budget_max is not None and budget_max > 0:
        message = f"Here are elegant {label} options under Rs {budget_max} for you."
    else:
        message = f"Here are curated premium {label} picks for you."

    if count > 0:
        message = f"{message} Found {count} options."

    if discount_label:
        message = f"{message} {discount_label}."

    return message


def build_greeting_message(display_name: str, discount_label: str | None = None) -> str:
    if display_name and display_name.lower() != "guest":
        message = f"Welcome back, {display_name}. I am here to curate premium looks for you today."
    else:
        message = "Welcome to ABFRL. I am here to curate premium looks for you today."

    if discount_label:
        message = f"{message} {discount_label}."

    return message
