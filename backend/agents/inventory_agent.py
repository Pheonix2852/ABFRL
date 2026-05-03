"""
Inventory Agent — Stock lookup from Firebase Realtime DB with JSON fallback.
"""

import json
import os
import logging

from agents.firebase_client import FIREBASE_AVAILABLE, get_ref

logger = logging.getLogger(__name__)

STORE_ALIASES = {
    "online": "online_warehouse",
    "warehouse": "online_warehouse",
    "online_warehouse": "online_warehouse",
    "mumbai": "store_mumbai",
    "store_mumbai": "store_mumbai",
    "delhi": "store_delhi",
    "store_delhi": "store_delhi",
    "bangalore": "store_bangalore",
    "bengaluru": "store_bangalore",
    "store_bangalore": "store_bangalore",
}

STORE_LABELS = {
    "online_warehouse": "Online Warehouse",
    "store_mumbai": "Mumbai Store",
    "store_delhi": "Delhi Store",
    "store_bangalore": "Bangalore Store",
}

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


def normalize_store_key(store: str | None) -> str:
    if not store:
        return "online_warehouse"

    key = str(store).strip().lower()
    return STORE_ALIASES.get(key, "online_warehouse")


def pretty_store_label(store: str | None) -> str:
    normalized = normalize_store_key(store)
    return STORE_LABELS.get(normalized, normalized.replace("_", " ").title())


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
    resolved_store = normalize_store_key(store)
    store_label = pretty_store_label(resolved_store)
    sku_data = _get_sku_data(sku_id)

    if not sku_data:
        return {
            "sku_id": sku_id,
            "store": resolved_store,
            "store_label": store_label,
            "online_stock": 0,
            "in_stock": False,
            "total_stock_all_stores": 0,
            "store_breakdown": {},
            "message": f"SKU '{sku_id}' not found in inventory.",
        }

    store_data = sku_data.get(resolved_store, {"quantity": 0, "in_stock": False})
    total = sum(v["quantity"] for v in sku_data.values())

    # Build per-store breakdown
    store_breakdown = {}
    for store_name, store_info in sku_data.items():
        store_breakdown[store_name] = {
            "quantity": store_info["quantity"],
            "in_stock": store_info["in_stock"],
        }

    online_stock = sku_data.get("online_warehouse", {}).get("quantity", 0)
    is_in_stock = store_data.get("in_stock", False)
    store_qty = int(store_data.get("quantity", 0) or 0)

    if is_in_stock:
        message = (
            f"{sku_id} is available at {store_label}: {store_qty} units. "
            f"Online stock: {online_stock}. Total across all stores: {total}."
        )
    else:
        message = (
            f"{sku_id} is currently out of stock at {store_label}. "
            f"Online stock: {online_stock}. Total across all stores: {total}."
        )

    return {
        "sku_id": sku_id,
        "store": resolved_store,
        "store_label": store_label,
        "store_stock": store_qty,
        "online_stock": online_stock,
        "in_stock": is_in_stock,
        "total_stock_all_stores": total,
        "store_breakdown": store_breakdown,
        "message": message,
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
