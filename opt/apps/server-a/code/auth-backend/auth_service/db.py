from typing import Any

from django.conf import settings
from mongoengine import connect

_connection: Any | None = None


def init_mongo() -> Any:
    global _connection  # noqa: WPS420
    if _connection is not None:
        return _connection
    _connection = connect(
        alias="default",
        host=settings.MONGO_URI,
        db=settings.MONGO_DB,
        uuidRepresentation="standard",
    )
    return _connection
