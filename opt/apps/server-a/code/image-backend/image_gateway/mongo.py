from functools import lru_cache

from django.conf import settings
from pymongo import MongoClient


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    return MongoClient(settings.MONGO_URI, tz_aware=True)


def get_db():
    return get_client()[settings.MONGO_DB]


def get_collection(name: str):
    return get_db()[name]


def ping() -> bool:
    get_client().admin.command("ping")
    return True
