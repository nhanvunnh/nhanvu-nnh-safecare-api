import datetime

from .mongo import get_collection


COLLECTION = "image_cache_cleanup_logs"


def write_cleanup_log(*, folder: str, status: str, message: str, bytes_before: int, bytes_after: int, files_deleted: int):
    doc = {
        "timeCreate": datetime.datetime.utcnow(),
        "folder": folder,
        "status": status,
        "message": message or "",
        "bytes_before": int(bytes_before or 0),
        "bytes_after": int(bytes_after or 0),
        "files_deleted": int(files_deleted or 0),
    }
    try:
        get_collection(COLLECTION).insert_one(doc)
    except Exception:
        pass
