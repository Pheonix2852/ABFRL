"""
Inventory Agent — Stock lookup from Firebase Realtime DB with JSON fallback.
"""

import json
import os
import logging

from agents.firebase_client import FIREBASE_AVAILABLE, get_ref

logger = logging.getLogger(__name__)

# Path to local JSON fallback
_inventory_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "inventory.json")
)


def _load_local_inventory() -> dict:
    """Load inventory from local JSON file."""
    with open(_inventory_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_sku_data(sku_id: str) -> dict:
    """
    Fetch SKU data from Firebase first, fall back to local JSON.
    Returns the dict for a single SKU or {} if not found.
    """
    if FIREBASE_AVAILABLE:
        try:
            data = get_ref(f"/inventory/{sku_id}").get()
            if data is not None:
                return data
            logger.warning("SKU '%s' not found in Firebase, falling back to JSON.", sku_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Firebase read failed for SKU '%s': %s — falling back to JSON.", sku_id, exc)

    # Fallback to local JSON
    inventory = _load_local_inventory()
    return inventory.get(sku_id, {})


def run(sku_id: str, store: str = "online_warehouse") -> dict:
    """
    Check stock for a SKU.

    Args:
        sku_id: Product SKU e.g. "SKU_001"
        store:  Store key — "online_warehouse", "store_mumbai",
                "store_delhi", or "store_bangalore"

    Returns:
        dict with sku_id, online_stock, in_stock, total_stock_all_stores,
        and per-store breakdown.
    """
    sku_data = _get_sku_data(sku_id)

    if not sku_data:
        return {
            "sku_id": sku_id,
            "online_stock": 0,
            "in_stock": False,
            "total_stock_all_stores": 0,
            "store_breakdown": {},
            "message": f"SKU '{sku_id}' not found in inventory.",
        }

    store_data = sku_data.get(store, {"quantity": 0, "in_stock": False})
    total = sum(v["quantity"] for v in sku_data.values())

    # Build per-store breakdown
    store_breakdown = {}
    for store_name, store_info in sku_data.items():
        store_breakdown[store_name] = {
            "quantity": store_info["quantity"],
            "in_stock": store_info["in_stock"],
        }

    online_stock = sku_data.get("online_warehouse", {}).get("quantity", 0)
    is_in_stock = store_data["in_stock"]

    return {
        "sku_id": sku_id,
        "online_stock": online_stock,
        "in_stock": is_in_stock,
        "total_stock_all_stores": total,
        "store_breakdown": store_breakdown,
        "message": (
            f"{sku_id}: {online_stock} units online, {total} total across all stores."
            if is_in_stock
            else f"{sku_id}: Out of stock at {store}. {total} total across all stores."
        ),
    }


def check_product_stock(sku_id: str) -> dict:
    """
    Quick check: is this product available online?
    Used by recommendation_agent to filter out-of-stock products.
    """
    sku_data = _get_sku_data(sku_id)
    online = sku_data.get("online_warehouse", {"quantity": 0, "in_stock": False})
    return {
        "quantity": online["quantity"],
        "in_stock": online["in_stock"],
    }
