from __future__ import annotations

import re
from typing import Any

_INVALID_NAMES = {
    "",
    "guest",
    "unknown",
    "none",
    "null",
    "n/a",
    "na",
}


def sanitize_name(name: Any) -> str | None:
    if name is None:
        return None

    raw = str(name).strip()
    if not raw:
        return None

    cleaned = re.sub(r"\s+", " ", raw)
    cleaned = re.sub(r"[^A-Za-z .'-]", "", cleaned).strip()
    if not cleaned:
        return None

    if cleaned.lower() in _INVALID_NAMES:
        return None

    return cleaned


def fallback_guest() -> str:
    return "Guest"


def _name_from_profile(profile: Any) -> str | None:
    if not isinstance(profile, dict):
        return None

    for key in ("name", "display_name", "first_name", "firstName"):
        candidate = sanitize_name(profile.get(key))
        if candidate:
            return candidate

    return None


def get_display_name(user_id: str, session_context: dict | None = None) -> str:
    del user_id

    if isinstance(session_context, dict):
        for key in ("profile", "user_profile", "customer_profile"):
            candidate = _name_from_profile(session_context.get(key))
            if candidate:
                return candidate

        for key in ("name", "display_name", "first_name", "firstName"):
            candidate = sanitize_name(session_context.get(key))
            if candidate:
                return candidate

    return fallback_guest()
