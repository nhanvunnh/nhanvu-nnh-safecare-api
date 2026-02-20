from pymongo import ASCENDING

from .mongo import get_collection


INDEX_DEFINITIONS = {
    "sms_messages": [
        {
            "name": "status_lease_priority_created",
            "fields": [
                ("status", ASCENDING),
                ("lease_until", ASCENDING),
                ("priority_weight", ASCENDING),
                ("created_at", ASCENDING),
            ],
        },
        {
            "name": "agent_status_lease_priority_created",
            "fields": [
                ("agent_id", ASCENDING),
                ("status", ASCENDING),
                ("lease_until", ASCENDING),
                ("priority_weight", ASCENDING),
                ("created_at", ASCENDING),
            ],
        },
        {"name": "request_id_idx", "fields": [("request_id", ASCENDING)]},
        {"name": "agent_status_idx", "fields": [("agent_id", ASCENDING), ("status", ASCENDING)]},
        {"name": "to_created_idx", "fields": [("to", ASCENDING), ("created_at", ASCENDING)]},
    ],
    "templates": [
        {"name": "approved_idx", "fields": [("approved", ASCENDING)]},
    ],
    "agents": [
        {"name": "last_seen_idx", "fields": [("last_seen_at", ASCENDING)]},
    ],
    "api_keys": [
        {"name": "is_active_idx", "fields": [("is_active", ASCENDING)]},
    ],
    "app_config": [
        {"name": "key_unique_idx", "fields": [("key", ASCENDING)], "unique": True},
    ],
}


def create_indexes() -> None:
    for collection_name, defs in INDEX_DEFINITIONS.items():
        collection = get_collection(collection_name)
        for definition in defs:
            collection.create_index(
                definition["fields"],
                name=definition["name"],
                unique=definition.get("unique", False),
            )
