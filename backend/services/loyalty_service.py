from __future__ import annotations

TIER_DISCOUNTS = {
    "bronze": 0.05,
    "silver": 0.10,
    "gold": 0.15,
    "platinum": 0.20,
}


def get_customer_tier(user_id: str) -> str:
    del user_id
    return "bronze"


def get_discount_pct(tier: str) -> float:
    return TIER_DISCOUNTS.get(str(tier or "bronze").lower(), 0.05)


def build_discount_message(tier: str) -> str:
    normalized_tier = str(tier or "bronze").lower()
    discount_pct = int(round(get_discount_pct(normalized_tier) * 100))
    return f"{discount_pct}% {normalized_tier.capitalize()} Member Benefit Applied"


def build_loyalty_payload(user_id: str) -> dict:
    tier = get_customer_tier(user_id)
    discount_pct = get_discount_pct(tier)
    discount_label = build_discount_message(tier)

    return {
        "tier": tier,
        "discount_pct": discount_pct,
        "discount_label": discount_label,
        "loyalty_points": 0,
        "customer_name": "Guest",
        "applicable_coupons": [],
        "message": f"Welcome! You are a {tier.capitalize()} member. {discount_label}.",
    }
