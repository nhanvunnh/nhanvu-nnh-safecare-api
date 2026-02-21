from functools import lru_cache

from django.conf import settings
from pymongo import MongoClient


@lru_cache(maxsize=1)
def get_client():
    return MongoClient(settings.MONGO_URI, tz_aware=True)


@lru_cache(maxsize=1)
def get_sync_client():
    return MongoClient(settings.SYNC_MONGO_URI, tz_aware=True)


def get_db():
    return get_client()[settings.MONGO_DB]


def get_collection(name: str):
    return get_db()[name]


def get_target_collection(db_name: str, collection_name: str):
    return get_sync_client()[db_name][collection_name]
