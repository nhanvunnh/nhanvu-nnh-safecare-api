import os
import threading
import time

from .cleanup_log import write_cleanup_log

_CLEANUP_LOCK = threading.Lock()
_LAST_CLEANUP = {}


def _dir_size_bytes(root):
    total = 0
    for base, _, files in os.walk(root):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(base, name))
            except Exception:
                pass
    return total


def _cleanup_cache_dir(cache_dir, max_bytes, max_days):
    files = []
    now = time.time()
    for base, _, names in os.walk(cache_dir):
        for name in names:
            path = os.path.join(base, name)
            try:
                st = os.stat(path)
                files.append((path, st.st_mtime, st.st_size))
            except Exception:
                pass
    bytes_before = sum(f[2] for f in files)
    files_deleted = 0

    if max_days:
        cutoff = now - (max_days * 86400)
        for path, mtime, _ in list(files):
            if mtime < cutoff:
                try:
                    os.remove(path)
                    files_deleted += 1
                except Exception:
                    pass

    files = []
    for base, _, names in os.walk(cache_dir):
        for name in names:
            path = os.path.join(base, name)
            try:
                st = os.stat(path)
                files.append((path, st.st_mtime, st.st_size))
            except Exception:
                pass
    files.sort(key=lambda x: x[1])
    total = sum(f[2] for f in files)

    if max_bytes and total > max_bytes:
        for path, _, size in files:
            if total <= max_bytes:
                break
            try:
                os.remove(path)
                total -= size
                files_deleted += 1
            except Exception:
                pass

    bytes_after = _dir_size_bytes(cache_dir)
    return bytes_before, bytes_after, files_deleted


def maybe_cleanup_cache_async(cache_dir, max_bytes, max_days, min_interval_seconds=300):
    now = time.time()
    last = _LAST_CLEANUP.get(cache_dir, 0)
    if now - last < min_interval_seconds:
        return
    if not _CLEANUP_LOCK.acquire(blocking=False):
        return
    _LAST_CLEANUP[cache_dir] = now

    def _run():
        status = "success"
        message = ""
        bytes_before = 0
        bytes_after = 0
        files_deleted = 0
        try:
            bytes_before, bytes_after, files_deleted = _cleanup_cache_dir(cache_dir, max_bytes, max_days)
        except Exception as exc:
            status = "error"
            message = str(exc)
        finally:
            write_cleanup_log(
                folder=cache_dir,
                status=status,
                message=message,
                bytes_before=bytes_before,
                bytes_after=bytes_after,
                files_deleted=files_deleted,
            )
            _CLEANUP_LOCK.release()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
