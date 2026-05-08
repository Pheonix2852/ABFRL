from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz, process


_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_TAXONOMY_PATH = _DATA_DIR / "taxonomy.json"
_SYNONYMS_PATH = _DATA_DIR / "synonyms.json"
_PRODUCTS_PATH = _DATA_DIR / "products.json"

CANONICAL_CATEGORIES = {"ethnic_wear", "western_wear", "footwear", "accessories"}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
            return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


@lru_cache(maxsize=1)
def load_taxonomy() -> dict[str, list[str]]:
    raw = _load_json(_TAXONOMY_PATH)
    return {
        str(canonical).strip().lower(): [str(alias).strip().lower() for alias in aliases or [] if str(alias).strip()]
        for canonical, aliases in raw.items()
        if str(canonical).strip()
    }


@lru_cache(maxsize=1)
def load_synonyms() -> dict[str, list[str]]:
    raw = _load_json(_SYNONYMS_PATH)
    return {
        str(canonical).strip().lower(): [str(alias).strip().lower() for alias in aliases or [] if str(alias).strip()]
        for canonical, aliases in raw.items()
        if str(canonical).strip()
    }


@lru_cache(maxsize=1)
def _family_alias_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for canonical, aliases in load_taxonomy().items():
        index[canonical] = canonical
        for alias in aliases:
            index[alias] = canonical
    return index


@lru_cache(maxsize=1)
def _family_terms() -> list[str]:
    return sorted(_family_alias_index().keys(), key=len, reverse=True)


@lru_cache(maxsize=1)
def _color_alias_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for canonical, aliases in load_synonyms().items():
        index[canonical] = canonical
        for alias in aliases:
            index[alias] = canonical
    return index


@lru_cache(maxsize=1)
def _known_color_terms() -> list[str]:
    return sorted(_color_alias_index().keys(), key=len, reverse=True)


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    return text or None


def _best_fuzzy_match(text: str, choices: Iterable[str], score_cutoff: int = 85) -> str | None:
    choice_list = list(dict.fromkeys(choice for choice in choices if choice))
    if not choice_list:
        return None
    match = process.extractOne(text, choice_list, scorer=fuzz.ratio, score_cutoff=score_cutoff)
    if match:
        return str(match[0])
    return None


def normalize_term(term: str | None) -> str | None:
    text = _normalize_text(term)
    if not text:
        return None

    if text in CANONICAL_CATEGORIES:
        return text

    exact = _family_alias_index().get(text)
    if exact:
        return exact

    fuzzy = _best_fuzzy_match(text, _family_terms(), score_cutoff=84)
    if fuzzy:
        return _family_alias_index().get(fuzzy, fuzzy)

    return text


def normalize_color(color: str | None) -> str | None:
    text = _normalize_text(color)
    if not text:
        return None

    exact = _color_alias_index().get(text)
    if exact:
        return exact

    fuzzy = _best_fuzzy_match(text, _known_color_terms(), score_cutoff=82)
    if fuzzy:
        return _color_alias_index().get(fuzzy, fuzzy)

    return text


def _product_records() -> list[dict[str, Any]]:
    raw = _load_json(_PRODUCTS_PATH)
    if not raw:
        return []
    if isinstance(raw, dict):
        return [value for value in raw.values() if isinstance(value, dict)]
    return [item for item in raw if isinstance(item, dict)]


@lru_cache(maxsize=1)
def _family_category_index() -> dict[str, str]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for product in _product_records():
        category = _normalize_text(product.get("category"))
        subcategory = normalize_term(product.get("subcategory"))
        if not category or not subcategory:
            continue
        counts[subcategory][category] += 1
        for alias in expand_aliases(subcategory):
            counts[alias][category] += 1

    index: dict[str, str] = {}
    for family, counter in counts.items():
        if counter:
            index[family] = counter.most_common(1)[0][0]
    return index


def normalize_category(term: str | None) -> str | None:
    normalized = normalize_term(term)
    if not normalized:
        return None
    if normalized in CANONICAL_CATEGORIES:
        return normalized
    return get_category_for_family(normalized)


def normalize_query_text(query: str | None) -> str:
    text = _normalize_text(query)
    if not text:
        return ""

    tokens = re.findall(r"[a-zA-Z][a-zA-Z\-']*|\d+|[₹$]", text)
    normalized_tokens: list[str] = []
    known_terms = list(dict.fromkeys([*_family_terms(), *_known_color_terms()]))

    for token in tokens:
        if token.isdigit() or token in {"₹", "$"}:
            normalized_tokens.append(token)
            continue

        mapped = normalize_term(token) or normalize_color(token)
        if mapped:
            normalized_tokens.append(mapped)
            continue

        fuzzy = _best_fuzzy_match(token, known_terms, score_cutoff=80)
        if fuzzy:
            normalized_tokens.append(_family_alias_index().get(fuzzy) or _color_alias_index().get(fuzzy) or fuzzy)
            continue

        normalized_tokens.append(token)

    return " ".join(normalized_tokens)


def expand_aliases(term: str | None) -> list[str]:
    normalized = normalize_term(term)
    if not normalized:
        return []
    aliases = load_taxonomy().get(normalized, [])
    return sorted({normalized, *aliases})


def detect_explicit_product_noun(query: str | None) -> str | None:
    normalized_query = normalize_query_text(query)
    if not normalized_query:
        return None

    for canonical, aliases in load_taxonomy().items():
        candidates = [canonical, *aliases]
        for candidate in sorted(candidates, key=len, reverse=True):
            if candidate and candidate in normalized_query:
                return canonical

    for token in normalized_query.split():
        family = _family_alias_index().get(token)
        if family:
            return family

    return None


def get_category_for_family(family: str | None) -> str | None:
    normalized = normalize_term(family)
    if not normalized:
        return None

    if normalized in CANONICAL_CATEGORIES:
        return normalized

    return _family_category_index().get(normalized)


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
