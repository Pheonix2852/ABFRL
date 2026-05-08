from __future__ import annotations

from services.taxonomy_service import (
    detect_explicit_product_noun,
    expand_aliases,
    get_category_for_family,
    is_family_match,
    load_synonyms,
    load_taxonomy,
    normalize_category,
    normalize_color,
    normalize_query_text,
    normalize_term,
    preferred_families,
)
