"""
Orchestrator Agent — Routes NLU output to the correct agents and assembles the final response.
This is the ONLY file that imports other agents.
"""

import os
import logging
from groq import Groq

from config import USE_NEW_LOYALTY, USE_NEW_TONE
from agents import nlu_agent
from agents import recommendation_agent
from agents import inventory_agent
from agents import loyalty_agent
from services import loyalty_service, profile_service, tone_service
from services import product_resolver

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
logger = logging.getLogger(__name__)

CONTINUATION_SIGNALS = [
    "more",
    "show more",
    "different color",
    "different colours",
    "cheaper",
    "another",
    "else",
    "other options",
    "blue",
    "formal",
    "casual",
]


def build_conversation_context(session: dict) -> str:
    """
    Build a readable conversation context string from the last 3 turns
    in the session history.

    Args:
        session: Session dict containing a 'history' list of
                 {"user": str, "agent": str} turn dicts.

    Returns:
        Formatted string of the last 3 turns, or empty string if
        history is absent / empty.
    """
    history = session.get("history", [])
    if not history:
        return ""

    # Take only the last 3 turns to keep the context concise
    recent = history[-3:]

    lines = ["Previous conversation:"]
    for turn in recent:
        lines.append(f"User: {turn.get('user', '')}")
        lines.append(f"Assistant: {turn.get('agent', '')}")

    return "\n".join(lines)


import re


def is_continuation(message: str, intent: str, entities: dict) -> bool:
    """
    Stricter continuation detection: only treat as continuation when the
    message is short and contains an explicit follow-up phrase (whole-word
    match). Do NOT merge when the message contains strong entity hints.
    """
    lower = (message or "").lower().strip()
    # Avoid long messages being treated as follow-ups
    if len(lower.split()) > 4:
        return False

    # Do whole-word/phrase matching to avoid accidental substring matches
    has_signal = False
    for s in CONTINUATION_SIGNALS:
        pattern = r"\b" + re.escape(s) + r"\b"
        if re.search(pattern, lower):
            has_signal = True
            break

    if not has_signal:
        return False

    # If the user provided strong entity information, treat as a fresh query
    has_strong_entity = any(
        entities.get(key) for key in ["category", "subcategory", "budget_max", "budget_min", "color", "occasion"]
    )
    if has_strong_entity:
        return False

    return True


def run(message: str, user_id: str, session: dict) -> dict:
    """
    Main orchestration pipeline.

    1. Run NLU to extract intent + entities
    2. Route to appropriate agent(s)
    3. Assemble and return the response dict

    Args:
        message:  Raw user message
        user_id:  Customer ID from request
        session:  Session dict (with 'history' list) for context

    Returns:
        dict matching ChatResponse schema (minus session_id)
    """
    # Step 1: Build conversation context from session history
    conversation_context = build_conversation_context(session)
    recommendation_context = {
        "conversation": conversation_context,
        "previous_plan": session.get("last_resolved_intent"),
    }

    # Step 2: NLU — extract intent and entities (with context for recommendations)
    nlu_result = nlu_agent.run(message, context=conversation_context)
    intent = nlu_result.get("intent", "fallback")
    entities = nlu_result.get("entities", {})
    prior = session.get("last_resolved_intent") or {}
    has_search_context = any(
        entities.get(key)
        for key in ["gender", "category", "subcategory", "budget_max", "budget_min", "occasion", "color"]
    )

    if intent == "recommendation" and not has_search_context and prior.get("intent") != "recommendation":
        return _handle_clarification_prompt()

    if is_continuation(message, intent, entities):
        if prior.get("intent") == "recommendation":
            for key in [
                "gender",
                "category",
                "subcategory",
                "budget_max",
                "budget_min",
                "occasion",
                "color",
            ]:
                if not entities.get(key) and prior.get(key):
                    entities[key] = prior[key]

            msg = message.lower().strip()

            # cheaper = tighten budget
            if "cheaper" in msg:
                current_budget = entities.get("budget_max")
                if current_budget:
                    entities["budget_max"] = max(500, int(current_budget * 0.7))

            # different color = clear previous color preference
            if "different color" in msg or "different colours" in msg:
                entities["color"] = None

            # another / more = diversify result set hint
            if any(word in msg for word in ["more", "another", "else"]):
                entities["exclude_previous"] = True
        else:
            return _handle_clarification_prompt()

    print(f"[orchestrator] Intent: {intent} | Entities: {entities}")
    logger.info("[orchestrator] Intent: %s", intent)

    # Step 3: Route based on intent
    # Clear prior inventory search filters when moving into a fresh recommendation
    # request to avoid carrying over store-specific constraints.
    prior_intent = (session.get("last_resolved_intent") or {}).get("intent")
    if prior_intent == "inventory_check" and intent == "recommendation":
        session["last_resolved_intent"] = {}

    if intent == "greeting":
        return _handle_greeting(user_id, session)

    if intent == "recommendation":
        result = _handle_recommendation(
            entities,
            user_id,
            session,
            context=recommendation_context,
            message=message,
        )
        # Save previous search filters
        session["last_resolved_intent"] = {
            "intent": "recommendation",
            "gender": entities.get("gender"),
            "category": entities.get("category"),
            "subcategory": entities.get("subcategory"),
            "budget_max": entities.get("budget_max"),
            "budget_min": entities.get("budget_min"),
            "occasion": entities.get("occasion"),
            "color": entities.get("color"),
        }

        # Save shown product IDs
        session["last_product_ids"] = [
            p.get("id") for p in result.get("products", []) if p.get("id")
        ]
        return result

    if intent == "inventory_check":
        return _handle_inventory_check(entities, user_id=user_id, message=message)

    if intent == "loyalty_check":
        return _handle_loyalty_check(user_id)

    # fallback
    return _handle_fallback()


def _build_greeting_prompt(display_name: str, tier: str, discount_label: str, points: int = 0) -> str:
    name = display_name.split()[0] if display_name and display_name != "Guest" else "there"
    safe_tier = (tier or "bronze").capitalize()

    return (
        "You are a warm, personal style assistant for ABFRL, India's largest "
        "fashion retailer.\n"
        f"You are speaking to {name}, a {safe_tier} tier member.\n"
        f"Their current discount: {discount_label}.\n"
        f"They have {points} loyalty points.\n"
        "Keep the welcome under 2 sentences. Address them by first name when available.\n"
        "Do not claim browsing history, past purchases, or personal facts that are not provided."
    )


def _handle_greeting(user_id: str, session: dict) -> dict:
    """Handle greeting intent — return a friendly welcome."""
    display_name = profile_service.get_display_name(user_id, session)

    if USE_NEW_LOYALTY:
        discount_result = loyalty_service.build_loyalty_payload(user_id)
        tier = discount_result.get("tier", "bronze")
        points = int(discount_result.get("loyalty_points", 0) or 0)
    else:
        discount_result = loyalty_agent.run(user_id=user_id)
        customer = loyalty_agent.find_customer(user_id) or {}
        tier = customer.get("loyaltyTier", discount_result.get("tier", "bronze"))
        points = int(customer.get("loyaltyPoints", discount_result.get("loyalty_points", 0)) or 0)

    if display_name != "Guest":
        prompt = _build_greeting_prompt(
            display_name=display_name,
            tier=tier,
            discount_label=discount_result.get("discount_label", "No discount"),
            points=points,
        )
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=120,
            )
            message = response.choices[0].message.content.strip()
        except Exception:
            message = tone_service.build_greeting_message(display_name, discount_result.get("discount_label"))
    else:
        message = tone_service.build_greeting_message(display_name, discount_result.get("discount_label"))

    if USE_NEW_TONE:
        message = tone_service.build_greeting_message(display_name, discount_result.get("discount_label"))

    return {
        "intent": "greeting",
        "message": message,
        "products": [],
        "discount_info": discount_result.get("discount_label", None),
        "metadata": {
            "loyalty_tier": tier,
            "loyalty_discount_pct": int(discount_result.get("discount_pct", 0) * 100),
        },
    }


def _handle_recommendation(
    entities: dict,
    user_id: str,
    session: dict,
    context: dict | None = None,
    message: str = "",
) -> dict:
    """
    Handle recommendation intent.
    Always runs loyalty_agent alongside so discount is baked into results.
    """
    # Get loyalty/discount info first
    category = entities.get("category", "")
    if USE_NEW_LOYALTY:
        discount_info = loyalty_service.build_loyalty_payload(user_id)
    else:
        discount_info = loyalty_agent.run(
            user_id=user_id,
            cart_total=entities.get("budget_max", 0) or 0,
            category=category,
        )

    # Run recommendation agent with entities + discount context
    rec_result = recommendation_agent.run(
        entities=entities,
        user_id=user_id,
        discount_info=discount_info,
        exclude_ids=session.get("last_product_ids", []),
        strict_subcategory=True,
        message=message,
        context=context,
    )

    metadata_tier = discount_info.get("tier", "bronze")
    if not USE_NEW_LOYALTY:
        customer = loyalty_agent.find_customer(user_id)
        if customer and customer.get("loyaltyTier"):
            metadata_tier = customer.get("loyaltyTier")

    return {
        "intent": "recommendation",
        "message": rec_result.get("message", ""),
        "products": rec_result.get("products", []),
        "discount_info": discount_info.get("discount_label", None),
        "metadata": {
            "loyalty_tier": metadata_tier,
            "loyalty_discount_pct": int(discount_info.get("discount_pct", 0) * 100),
        },
    }


def _build_inventory_product_card(
    product: dict,
    sku_id: str,
    online_stock: int,
    store_in_stock: bool,
    store_label: str | None,
    store_stock: int,
) -> dict:
    availability_badge = None
    if store_label:
        availability_badge = (
            f"Available in {store_label.replace(' Store', '')} • {int(store_stock)} units"
            if store_in_stock
            else f"Out of stock in {store_label.replace(' Store', '')}"
        )

    return {
        "id": str(product.get("id") or sku_id),
        "name": str(product.get("name") or "Product"),
        "category": str(product.get("category") or ""),
        "subcategory": str(product.get("subcategory") or ""),
        "gender_tags": list(product.get("gender_tags") or []),
        "price": float(product.get("price") or 0),
        "discounted_price": None,
        "colors": list(product.get("colors") or []),
        "occasion_tags": list(product.get("occasionTags") or product.get("occasion_tags") or []),
        "sizes": list(product.get("sizes") or []),
        "online_stock": int(online_stock),
        "in_stock": bool(store_in_stock),
        "image_url": str(product.get("image_url") or product.get("imageUrl") or ""),
        "rating": float(product.get("rating") or 0),
        "why_for_you": "",
        "availability_badge": availability_badge,
    }


def _handle_inventory_check(entities: dict, user_id: str, message: str = "") -> dict:
    """Handle inventory check intent."""
    sku_id = entities.get("sku_id")
    store = entities.get("store", "online_warehouse")
    resolved_product = None

    if not sku_id:
        resolved_product = product_resolver.resolve_product(
            query=message,
            subcategory=entities.get("subcategory"),
        )
        if resolved_product:
            sku_id = resolved_product.get("sku_id")

    if not sku_id:
        return {
            "intent": "inventory_check",
            "message": (
                "I'd love to check stock for you! "
                "Please specify a product (e.g. 'Is Anarkali Kurta Set available in Bangalore?')."
            ),
            "products": [],
            "discount_info": None,
            "metadata": None,
        }

    result = inventory_agent.run(sku_id=sku_id, store=store)

    products = []
    metadata = None
    product_payload = None

    if resolved_product and isinstance(resolved_product.get("product"), dict):
        product_payload = resolved_product.get("product")
    elif entities.get("sku_id"):
        direct = product_resolver.resolve_product(query=str(entities.get("sku_id")))
        if direct and isinstance(direct.get("product"), dict):
            product_payload = direct.get("product")

    # Build full rich product using recommendation pipeline helpers so the
    # frontend receives identical product shapes as normal recommendations.
    if product_payload:
        # Get discount info for pricing
        if USE_NEW_LOYALTY:
            discount_info = loyalty_service.build_loyalty_payload(user_id)
        else:
            discount_info = loyalty_agent.run(user_id=user_id)

        rich = recommendation_agent.build_rich_product(
            product=product_payload,
            entities=entities,
            discount_info=discount_info,
            online_stock=result.get("online_stock", 0),
            in_stock=result.get("in_stock", False),
        )

        # Add availability badge on top of the rich product
        availability_badge = None
        store_label = result.get("store_label")
        if store_label:
            availability_badge = (
                f"Available in {store_label.replace(' Store', '')} • {int(result.get('store_stock', 0))} units"
                if result.get("in_stock")
                else f"Out of stock in {store_label.replace(' Store', '')}"
            )
            rich["availability_badge"] = availability_badge

        products = [rich]
        metadata = {
            "cta": "See Product",
            "resolved_sku": sku_id,
            "store": result.get("store"),
            "store_label": result.get("store_label"),
        }

    return {
        "intent": "inventory_check",
        "message": result.get("message", ""),
        "products": products,
        "discount_info": None,
        "metadata": metadata,
    }


def _handle_loyalty_check(user_id: str) -> dict:
    """Handle loyalty check intent."""
    if USE_NEW_LOYALTY:
        result = loyalty_service.build_loyalty_payload(user_id)
    else:
        result = loyalty_agent.run(user_id=user_id)

    # Build a rich message with coupon info
    message = result.get("message", "")
    coupons = result.get("applicable_coupons", [])
    if coupons:
        coupon_strs = [f"🎟️ {c['code']}" for c in coupons]
        message += f"\n\nAvailable coupons: {', '.join(coupon_strs)}"

    return {
        "intent": "loyalty_check",
        "message": message,
        "products": [],
        "discount_info": result.get("discount_label", None),
        "metadata": {
            "loyalty_tier": result.get("tier", "bronze"),
            "loyalty_discount_pct": int(result.get("discount_pct", 0) * 100),
        },
    }


def _handle_fallback() -> dict:
    """Handle unrecognized intent."""
    return {
        "intent": "fallback",
        "message": (
            "I'm not sure I understood that. I can help you with:\n"
            "🛍️ Product recommendations — 'Show me red kurtas for Diwali'\n"
            "📦 Inventory checks — 'Is SKU_004 available in Mumbai?'\n"
            "⭐ Loyalty info — 'What's my loyalty tier?'\n\n"
            "What would you like to explore?"
        ),
        "products": [],
        "discount_info": None,
        "metadata": None,
    }


def _handle_clarification_prompt() -> dict:
    return {
        "intent": "fallback",
        "message": "What type of clothing would you like to explore today?",
        "products": [],
        "discount_info": None,
        "metadata": None,
    }
