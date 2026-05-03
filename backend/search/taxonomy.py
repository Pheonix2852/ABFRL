from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_TAXONOMY_PATH = _DATA_DIR / "taxonomy.json"
_SYNONYMS_PATH = _DATA_DIR / "synonyms.json"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


@lru_cache(maxsize=1)
def load_taxonomy() -> dict[str, list[str]]:
    raw = _load_json(_TAXONOMY_PATH)
    return {
        str(canonical).lower(): [str(alias).lower() for alias in aliases or []]
        for canonical, aliases in raw.items()
        if canonical
    }


@lru_cache(maxsize=1)
def load_synonyms() -> dict[str, list[str]]:
    raw = _load_json(_SYNONYMS_PATH)
    return {
        str(canonical).lower(): [str(alias).lower() for alias in aliases or []]
        for canonical, aliases in raw.items()
        if canonical
    }


def _normalize_with_lookup(word: str | None, lookup: dict[str, list[str]]) -> str | None:
    if word is None:
        return None

    text = str(word).strip().lower()
    if not text:
        return None

    for canonical in lookup:
        if text == canonical:
            return canonical

    for canonical, aliases in lookup.items():
        candidates = [canonical, *aliases]
        for candidate in sorted(candidates, key=len, reverse=True):
            if candidate and candidate in text:
                return canonical

    return text


def normalize_category(word: str | None) -> str | None:
    return _normalize_with_lookup(word, load_taxonomy())


def normalize_color(word: str | None) -> str | None:
    normalized = _normalize_with_lookup(word, load_synonyms())
    return normalized
