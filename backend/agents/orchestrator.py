"""
Orchestrator Agent — Routes NLU output to the correct agents and assembles the final response.
This is the ONLY file that imports other agents.
"""

import os
import logging
from groq import Groq

from agents import nlu_agent
from agents import recommendation_agent
from agents import inventory_agent
from agents import loyalty_agent

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
logger = logging.getLogger(__name__)

CONTINUATION_SIGNALS = [
    "more",
    "show more",
    "different",
    "cheaper",
    "another",
    "else",
    "other options",
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


def is_continuation(message: str, intent: str, entities: dict) -> bool:
    lower = message.lower().strip()
    is_short = len(lower.split()) <= 3
    has_signal = any(s in lower for s in CONTINUATION_SIGNALS)
    has_weak_intent = intent in ("fallback", "unclear", "")
    has_no_context = not any(
        entities.get(key) for key in ["category", "subcategory", "budget_max", "budget_min", "color", "occasion"]
    )
    return (is_short and has_signal) or (has_weak_intent and has_signal and has_no_context)


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
    if intent == "greeting":
        return _handle_greeting(user_id)

    elif intent == "recommendation":
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

    elif intent == "inventory_check":
        return _handle_inventory_check(entities)

    elif intent == "loyalty_check":
        return _handle_loyalty_check(user_id)

    else:  # fallback
        return _handle_fallback()


def _build_greeting_prompt(customer: dict, discount_info: dict) -> str:
    name = customer.get("name", "there").split()[0]
    tier = customer.get("loyaltyTier", "bronze").capitalize()
    discount_label = discount_info.get("discount_label", "No discount")
    points = customer.get("loyaltyPoints", 0)

    return (
        "You are a warm, personal style assistant for ABFRL, India's largest "
        "fashion retailer.\n"
        f"You are speaking to {name}, a {tier} tier member.\n"
        f"Their current discount: {discount_label}.\n"
        f"They have {points} loyalty points.\n"
        "Keep the welcome under 3 sentences. Address them by first name.\n"
        "Suggest one specific thing they might like based on their tier and history."
    )


def _handle_greeting(user_id: str) -> dict:
    """Handle greeting intent — return a friendly welcome."""
    discount_result = loyalty_agent.run(user_id=user_id)
    customer = loyalty_agent.find_customer(user_id)

    if customer and customer.get("name"):
        prompt = _build_greeting_prompt(customer, discount_result)
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=120,
            )
            message = response.choices[0].message.content.strip()
        except Exception:
            first_name = customer.get("name", "").split()[0]
            message = f"Hey {first_name}! 👋 Welcome back to ABFRL."
    else:
        message = (
            "Hello! 👋 Welcome to ABFRL Shopping Assistant. "
            "I can help you find fashion recommendations, check inventory, "
            "and apply loyalty discounts. What are you looking for today?"
        )

    return {
        "intent": "greeting",
        "message": message,
        "products": [],
        "discount_info": discount_result.get("discount_label", None),
        "metadata": {
            "loyalty_tier": customer.get("loyaltyTier", "bronze") if customer else "bronze",
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

    customer = loyalty_agent.find_customer(user_id)

    return {
        "intent": "recommendation",
        "message": rec_result.get("message", ""),
        "products": rec_result.get("products", []),
        "discount_info": discount_info.get("discount_label", None),
        "metadata": {
            "loyalty_tier": customer.get("loyaltyTier", "bronze")
            if customer
            else "bronze",
            "loyalty_discount_pct": int(discount_info.get("discount_pct", 0) * 100),
        },
    }


def _handle_inventory_check(entities: dict) -> dict:
    """Handle inventory check intent."""
    sku_id = entities.get("sku_id")
    store = entities.get("store", "online_warehouse")

    if not sku_id:
        return {
            "intent": "inventory_check",
            "message": (
                "I'd love to check stock for you! "
                "Please specify a product SKU (e.g. 'Is SKU_004 available?')."
            ),
            "products": [],
            "discount_info": None,
        }

    result = inventory_agent.run(sku_id=sku_id, store=store)

    return {
        "intent": "inventory_check",
        "message": result.get("message", ""),
        "products": [],
        "discount_info": None,
    }


def _handle_loyalty_check(user_id: str) -> dict:
    """Handle loyalty check intent."""
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
