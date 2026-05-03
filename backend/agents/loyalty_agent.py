"""
Loyalty Agent — Customer tier, discount calculation, and loyalty info.
Fetches customer data from Firebase Realtime DB with JSON fallback.
Loads promotions.json ONCE at module level.
"""

import json
import os
import logging

from agents.firebase_client import FIREBASE_AVAILABLE, get_ref

logger = logging.getLogger(__name__)

# Path to local JSON fallback for customers
_customers_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "customers.json")
)

# Load promotions ONCE at module level — NOT touched
_promotions_path = os.path.join(
    os.path.dirname(__file__), "..", "data", "promotions.json"
)

with open(os.path.abspath(_promotions_path), "r", encoding="utf-8") as f:
    PROMOTIONS = json.load(f)


def _load_local_customers() -> dict:
    """Load customers from local JSON file, indexed by ID."""
    with open(_customers_path, "r", encoding="utf-8") as f:
        customers_list = json.load(f)
    return {c["id"]: c for c in customers_list}


def find_customer(user_id: str) -> dict | None:
    """Look up a customer by ID — Firebase first, JSON fallback."""
    if FIREBASE_AVAILABLE:
        try:
            data = get_ref(f"/customers/{user_id}").get()
            if data is not None:
                return data
            logger.warning(
                "Customer '%s' not found in Firebase, falling back to JSON.", user_id
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Firebase read failed for customer '%s': %s — falling back to JSON.",
                user_id, exc,
            )

    # Fallback to local JSON
    customers = _load_local_customers()
    profile = customers.get(user_id)
    if profile is not None:
        return profile

    # Default guest profile for unknown user IDs
    return {
        "id": user_id,
        "name": "Guest",
        "loyaltyTier": "bronze",
        "loyaltyPoints": 0,
    }


def run(user_id: str, cart_total: float = 0, category: str = "") -> dict:
    """
    Calculate the best applicable discount for a customer.

    Args:
        user_id:    Customer ID e.g. "customer_001"
        cart_total:  Total value used to check coupon min order values
        category:   Product category for checking seasonal campaigns

    Returns:
        dict with tier, discount_pct, discount_label, loyalty_points,
        and optional coupon/campaign info.
    """
    customer = find_customer(user_id)

    if not customer:
        return {
            "tier": "bronze",
            "discount_pct": 0,
            "discount_label": "No discount",
            "loyalty_points": 0,
            "customer_name": "Guest",
            "message": "Welcome! You're a bronze member with 0 points.",
        }

    tier = customer["loyaltyTier"]
    tier_discount = PROMOTIONS.get("tierDiscounts", {}).get(tier, 0)
    loyalty_points = customer.get("loyaltyPoints", 0)
    customer_name = customer.get("name", "Customer")

    # Check seasonal campaigns for a potentially better deal
    best_discount = tier_discount
    best_label = f"{int(tier_discount * 100)}% {tier} Member Discount"

    if category:
        for campaign in PROMOTIONS.get("seasonalCampaigns", []):
            applicable_cats = campaign.get("applicableCategories", [])
            if category in applicable_cats or "all" in applicable_cats:
                campaign_discount = campaign.get("discountValue", 0)
                if campaign_discount > best_discount:
                    best_discount = campaign_discount
                    best_label = (
                        f"{int(campaign_discount * 100)}% "
                        f"{campaign['name']} Discount"
                    )

    # Check coupon codes for applicable ones
    applicable_coupons = []
    for coupon in PROMOTIONS.get("couponCodes", []):
        coupon_cats = coupon.get("applicableCategories", [])
        if "all" in coupon_cats or category in coupon_cats:
            if cart_total >= coupon.get("minOrderValue", 0):
                applicable_coupons.append({
                    "code": coupon["code"],
                    "type": coupon["discountType"],
                    "value": coupon["discountValue"],
                })

    return {
        "tier": tier,
        "discount_pct": best_discount,
        "discount_label": best_label,
        "loyalty_points": loyalty_points,
        "customer_name": customer_name,
        "applicable_coupons": applicable_coupons,
        "message": (
            f"Welcome back, {customer_name}! "
            f"You're a {tier} member with {loyalty_points} points. "
            f"{best_label} applied."
        ),
    }
