"""
Firebase Realtime Database client.

Initializes Firebase Admin SDK once and exposes:
  - get_ref(path)        → firebase_admin.db.reference(path)
  - FIREBASE_AVAILABLE   → bool flag for other modules to check
"""

import os
import json
import logging

logger = logging.getLogger(__name__)

FIREBASE_AVAILABLE = False

try:
    import firebase_admin
    from firebase_admin import credentials, db

    _firebase_url = os.getenv("FIREBASE_URL")
    _cred_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
    _cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")

    if not _firebase_url or (not _cred_json and not _cred_path):
        logger.warning(
            "FIREBASE_URL or FIREBASE_CREDENTIALS_JSON/FIREBASE_CREDENTIALS_PATH not set — "
            "Firebase disabled, using local JSON fallback."
        )
    else:
        # Avoid duplicate initialization
        try:
            firebase_admin.get_app()
        except ValueError:
            # Prefer inline JSON credential, fall back to file path
            if _cred_json:
                cred = credentials.Certificate(json.loads(_cred_json))
            else:
                cred = credentials.Certificate(_cred_path)
            firebase_admin.initialize_app(cred, {"databaseURL": _firebase_url})

        FIREBASE_AVAILABLE = True
        logger.info("Firebase Admin SDK initialized successfully.")

except Exception as exc:  # noqa: BLE001
    logger.warning("Firebase initialization failed: %s — using local JSON fallback.", exc)
    FIREBASE_AVAILABLE = False


def get_ref(path: str):
    """Return a Firebase Realtime Database reference for the given path."""
    if not FIREBASE_AVAILABLE:
        return None
    return db.reference(path)
