from __future__ import annotations

from django.conf import settings

from .mongo import get_collection
from .utils import now_utc

REGISTRATION_SECRET_KEY = "agent_registration_secret"
APP_CONFIG_COLLECTION = "app_config"


def get_registration_secret() -> str:
    doc = get_collection(APP_CONFIG_COLLECTION).find_one({"key": REGISTRATION_SECRET_KEY})
    if doc and isinstance(doc.get("value"), str):
        return doc["value"]
    return settings.AGENT_REGISTRATION_SECRET or ""


def set_registration_secret(secret: str, updated_by: str) -> str:
    now = now_utc()
    get_collection(APP_CONFIG_COLLECTION).update_one(
        {"key": REGISTRATION_SECRET_KEY},
        {
            "$set": {
                "value": secret,
                "updated_at": now,
                "updated_by": updated_by,
            },
            "$setOnInsert": {
                "key": REGISTRATION_SECRET_KEY,
                "created_at": now,
            },
        },
        upsert=True,
    )
    return secret
