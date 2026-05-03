from __future__ import annotations

from collections.abc import Iterable

CANONICAL_CATEGORIES = {
    "ethnic_wear",
    "western_wear",
    "footwear",
    "accessories",
}

_FAMILY_ALIASES = {
    "shirt": {"shirt", "shirts", "formal shirt", "casual shirt"},
    "tshirt": {"tshirt", "t-shirt", "tee", "tees"},
    "polo": {"polo", "polo shirt"},
    "blazer": {"blazer", "blazers", "jacket", "jackets"},
    "top": {"top", "tops"},
    "dress": {"dress", "dresses", "gown", "one piece", "midi"},
    "jeans": {"jean", "jeans", "denim"},
    "pants": {"pant", "pants", "trouser", "trousers", "slacks", "bottoms"},
    "trousers": {"trouser", "trousers"},
    "kurta": {"kurta", "kurtas", "kurti", "kurti"},
    "saree": {"saree", "sarees", "sari"},
    "sneakers": {"sneaker", "sneakers"},
    "heels": {"heel", "heels"},
    "sandals": {"sandal", "sandals"},
    "loafers": {"loafer", "loafers"},
    "watch": {"watch", "watches"},
    "bag": {"bag", "bags", "handbag", "handbags", "backpack", "backpacks"},
    "belt": {"belt", "belts"},
    "wallet": {"wallet", "wallets"},
    "footwear_general": {"shoe", "shoes", "footwear"},
}

_FAMILY_TO_CATEGORY = {
    "shirt": "western_wear",
    "tshirt": "western_wear",
    "polo": "western_wear",
    "blazer": "western_wear",
    "top": "western_wear",
    "dress": "western_wear",
    "jeans": "western_wear",
    "pants": "western_wear",
    "trousers": "western_wear",
    "kurta": "ethnic_wear",
    "saree": "ethnic_wear",
    "sneakers": "footwear",
    "heels": "footwear",
    "sandals": "footwear",
    "loafers": "footwear",
    "footwear_general": "footwear",
    "watch": "accessories",
    "bag": "accessories",
    "belt": "accessories",
    "wallet": "accessories",
}

COLOR_MAP = {
    "red": ["red", "maroon", "crimson", "burgundy", "wine", "scarlet", "ruby", "coral"],
    "blue": ["blue", "navy", "royal blue", "sky blue", "teal"],
    "black": ["black", "jet black", "midnight black", "charcoal"],
    "white": ["white", "off-white", "ivory", "cream"],
    "green": ["green", "olive", "mint", "emerald"],
    "pink": ["pink", "blush pink", "rose"],
    "yellow": ["yellow", "mustard", "golden"],
    "purple": ["purple", "plum", "lavender", "violet"],
    "brown": ["brown", "tan", "beige", "camel"]
}

def normalize_color(color: str):
    if not color:
        return None

    c = color.strip().lower()

    for canonical, variants in COLOR_MAP.items():
        if c == canonical or c in variants:
            return canonical

    return c

def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    return text or None


def normalize_term(term: str | None) -> str | None:
    text = _normalize_text(term)
    if not text:
        return None

    if text in CANONICAL_CATEGORIES:
        return text

    for family, aliases in _FAMILY_ALIASES.items():
        if text == family or text in aliases:
            return family

    return text


def expand_aliases(term: str | None) -> list[str]:
    normalized = normalize_term(term)
    if not normalized:
        return []

    if normalized == "footwear_general":
        return ["sneakers", "loafers", "sandals", "heels"]

    aliases = _FAMILY_ALIASES.get(normalized)
    if not aliases:
        return [normalized]

    return sorted({normalized, *aliases})


def detect_explicit_product_noun(query: str | None) -> str | None:
    text = _normalize_text(query)
    if not text:
        return None

    # Match longer aliases first for deterministic behavior.
    candidates: list[tuple[str, str]] = []
    for family, aliases in _FAMILY_ALIASES.items():
        for alias in aliases:
            candidates.append((family, alias))
        candidates.append((family, family))

    for family, alias in sorted(candidates, key=lambda item: len(item[1]), reverse=True):
        if alias and alias in text:
            return family

    # Fuzzy match fallback: handle common typos (e.g., 'kuryas' -> 'kurta')
    try:
        from difflib import SequenceMatcher

        words = [w for w in text.split() if w]
        best_score = 0.0
        best_family = None
        for family, aliases in _FAMILY_ALIASES.items():
            for alias in aliases:
                for w in words:
                    score = SequenceMatcher(None, w, alias).ratio()
                    if score > best_score:
                        best_score = score
                        best_family = family

        # Threshold tuned to allow small typos but avoid false positives
        if best_score >= 0.7:
            return best_family
    except Exception:
        pass

    return None


def get_category_for_family(family: str | None) -> str | None:
    normalized = normalize_term(family)
    if not normalized:
        return None

    if normalized in CANONICAL_CATEGORIES:
        return normalized

    return _FAMILY_TO_CATEGORY.get(normalized)


def is_family_match(product_subcategory: str | None, requested_family: str | None) -> bool:
    normalized_product = normalize_term(product_subcategory)
    normalized_requested = normalize_term(requested_family)
    if not normalized_product or not normalized_requested:
        return False

    if normalized_product == normalized_requested:
        return True

    requested_aliases = set(expand_aliases(normalized_requested))
    product_aliases = set(expand_aliases(normalized_product))
    return bool(requested_aliases & product_aliases)


def preferred_families(family: str | None) -> Iterable[str]:
    return expand_aliases(family)
